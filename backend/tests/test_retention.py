"""Data retention: the platform-admin consent gate on User.retain_all_sessions
(PATCH /platform/users/{id}/retention), provider-scoped document uploads,
and services/retention_service.py's purge sweep."""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.clinical_note import ClinicalNote, NoteEntity
from app.models.encounter import AudioFile, Encounter
from app.models.patient import Patient
from app.models.transcript import Transcript, TranscriptEntity
from app.models.clinical_note import EntityType
from app.models.user import User, UserRole
from app.services import retention_service
from tests.conftest import TestSessionLocal, signup_clinic

settings = get_settings()


async def _make_platform_admin(email: str) -> None:
    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_platform_admin = True
        await session.commit()


async def _new_clinic_id(client: AsyncClient, operator_headers: dict) -> str:
    resp = await client.post(
        "/api/v1/platform/clinics", headers=operator_headers, json={"name": "Retention Test Clinic"}
    )
    return resp.json()["id"]


async def _new_doctor(client: AsyncClient, operator_headers: dict, clinic_id: str) -> dict:
    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator_headers,
        json={"email": f"doc-{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dr. Retention Test"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- API: the consent gate -------------------------------------------------


async def test_retention_toggle_refused_without_signed_consent(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])
    doctor = await _new_doctor(client, operator["headers"], clinic_id)
    assert doctor["retain_all_sessions"] is False

    resp = await client.patch(
        f"/api/v1/platform/users/{doctor['id']}/retention",
        headers=operator["headers"],
        json={"retain_all_sessions": True},
    )
    assert resp.status_code == 403, resp.text


async def test_retention_toggle_succeeds_once_consent_is_on_file(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])
    doctor = await _new_doctor(client, operator["headers"], clinic_id)

    upload_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/documents",
        headers=operator["headers"],
        data={"doc_type": "CONSENT_FORM", "provider_id": doctor["id"]},
        files={"file": ("consent.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    assert upload_resp.json()["provider_id"] == doctor["id"]

    resp = await client.patch(
        f"/api/v1/platform/users/{doctor['id']}/retention",
        headers=operator["headers"],
        json={"retain_all_sessions": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["retain_all_sessions"] is True

    # Turning it back off never needs a fresh consent check.
    off_resp = await client.patch(
        f"/api/v1/platform/users/{doctor['id']}/retention",
        headers=operator["headers"],
        json={"retain_all_sessions": False},
    )
    assert off_resp.status_code == 200, off_resp.text
    assert off_resp.json()["retain_all_sessions"] is False


async def test_document_upload_provider_id_must_belong_to_clinic(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_a = await _new_clinic_id(client, operator["headers"])
    clinic_b = await _new_clinic_id(client, operator["headers"])
    doctor_in_b = await _new_doctor(client, operator["headers"], clinic_b)

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_a}/documents",
        headers=operator["headers"],
        data={"doc_type": "CONSENT_FORM", "provider_id": doctor_in_b["id"]},
        files={"file": ("consent.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 404


async def test_document_upload_with_no_provider_is_clinic_wide(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/documents",
        headers=operator["headers"],
        data={"doc_type": "CONTRACT"},
        files={"file": ("contract.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["provider_id"] is None


# --- Purge sweep -------------------------------------------------------------


async def _make_provider(clinic_id: uuid.UUID, *, retain_all_sessions: bool = False) -> uuid.UUID:
    async with TestSessionLocal() as session:
        user = User(
            clinic_id=clinic_id,
            email=f"doc-{uuid.uuid4().hex[:8]}@example.com",
            full_name="Dr. Purge Test",
            role=UserRole.PROVIDER,
            hashed_password="x",
            retain_all_sessions=retain_all_sessions,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _make_patient(clinic_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        patient = Patient(
            clinic_id=clinic_id, first_name="Jane", last_name="Doe", date_of_birth=date(1985, 4, 12)
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient.id


async def _make_full_encounter(
    clinic_id: uuid.UUID, patient_id: uuid.UUID, provider_id: uuid.UUID, started_at: datetime
) -> uuid.UUID:
    """An encounter with an audio file, a transcript (+entity) and a signed
    note (+entity) attached — everything the purge sweep should remove."""
    async with TestSessionLocal() as session:
        encounter = Encounter(
            clinic_id=clinic_id,
            patient_id=patient_id,
            provider_id=provider_id,
            created_by_id=provider_id,
            started_at=started_at,
        )
        session.add(encounter)
        await session.flush()

        session.add(
            AudioFile(
                encounter_id=encounter.id,
                storage_path=f"/tmp/does-not-exist-{uuid.uuid4().hex}.webm",
                mime_type="audio/webm",
                uploaded_by_id=provider_id,
            )
        )
        transcript = Transcript(encounter_id=encounter.id, raw_text="Patient reports mild pain.", provider="whisper")
        session.add(transcript)
        await session.flush()
        session.add(
            TranscriptEntity(
                transcript_id=transcript.id, entity_type=EntityType.SYMPTOM, text="mild pain", line_index=0
            )
        )
        note = ClinicalNote(encounter_id=encounter.id, rendered_content="Patient reports mild pain.")
        session.add(note)
        await session.flush()
        session.add(
            NoteEntity(clinical_note_id=note.id, entity_type=EntityType.SYMPTOM, text="mild pain", line_index=0)
        )
        await session.commit()
        return encounter.id


async def test_purge_sweep_removes_content_and_stamps_encounter(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id_str = await _new_clinic_id(client, operator["headers"])
    clinic_id = uuid.UUID(clinic_id_str)
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    old_enough = datetime.now(timezone.utc) - timedelta(days=settings.retention_days + 1)
    encounter_id = await _make_full_encounter(clinic_id, patient_id, provider_id, old_enough)

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        purged = await retention_service.run_retention_sweep()
    assert purged == 1

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.content_purged_at is not None

        assert (
            await session.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Transcript).where(Transcript.encounter_id == encounter_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id))
        ).scalar_one_or_none() is None

        audit = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.action == "ENCOUNTER_CONTENT_PURGED", AuditLog.resource_id == str(encounter_id)
                )
            )
        ).scalar_one_or_none()
        assert audit is not None

    # Idempotent: a second sweep finds nothing left to do.
    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        purged_again = await retention_service.run_retention_sweep()
    assert purged_again == 0


async def test_purge_sweep_skips_encounters_within_the_retention_window(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    encounter_id = await _make_full_encounter(clinic_id, patient_id, provider_id, recent)

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        purged = await retention_service.run_retention_sweep()
    assert purged == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.content_purged_at is None
        assert (
            await session.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None


async def test_purge_sweep_skips_providers_with_retain_all_sessions(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id, retain_all_sessions=True)
    patient_id = await _make_patient(clinic_id)
    old_enough = datetime.now(timezone.utc) - timedelta(days=settings.retention_days + 1)
    encounter_id = await _make_full_encounter(clinic_id, patient_id, provider_id, old_enough)

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        purged = await retention_service.run_retention_sweep()
    assert purged == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.content_purged_at is None
        assert (
            await session.execute(select(Transcript).where(Transcript.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None
