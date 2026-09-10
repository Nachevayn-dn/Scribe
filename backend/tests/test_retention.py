"""Data retention: the platform-admin consent gate on User.retain_all_sessions
(PATCH /platform/users/{id}/retention), provider-scoped document uploads,
the two-stage retention sweep in services/retention_service.py (archive at
retention_audio_days, full purge at retention_record_days), and the
GET /encounters?archived filter."""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.clinical_note import ClinicalNote, EntityType, NoteEntity
from app.models.encounter import AudioFile, Encounter
from app.models.patient import Patient
from app.models.transcript import Transcript, TranscriptEntity
from app.models.user import User, UserRole
from app.services import retention_service
from tests.conftest import TestSessionLocal, create_user, signup_clinic

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


# --- Two-stage retention sweep ----------------------------------------------


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
    note (+entity) attached — everything the retention sweep can touch."""
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


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def test_archive_stage_removes_audio_only_and_stamps_archived_at(client: AsyncClient):
    """Past the audio-retention window: audio is gone, transcript/note stay
    — they're the medical record, kept until the 7-year floor."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    encounter_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_audio_days + 1)
    )

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    assert result.archived == 1
    assert result.purged == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.archived_at is not None
        assert encounter.content_purged_at is None

        assert (
            await session.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Transcript).where(Transcript.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None
        assert (
            await session.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None

        audit = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.action == "ENCOUNTER_ARCHIVED", AuditLog.resource_id == str(encounter_id)
                )
            )
        ).scalar_one_or_none()
        assert audit is not None

    # Idempotent: a second sweep finds nothing left to archive.
    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result_again = await retention_service.run_retention_sweep()
    assert result_again.archived == 0


async def test_archive_stage_skips_encounters_within_the_audio_window(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    encounter_id = await _make_full_encounter(clinic_id, patient_id, provider_id, _days_ago(1))

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    assert result.archived == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.archived_at is None
        assert (
            await session.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None


async def test_archive_stage_skips_providers_with_retain_all_sessions(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id, retain_all_sessions=True)
    patient_id = await _make_patient(clinic_id)
    encounter_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_audio_days + 1)
    )

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    assert result.archived == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.archived_at is None
        assert (
            await session.execute(select(AudioFile).where(AudioFile.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None


async def test_purge_stage_removes_transcript_and_note_at_record_retention_floor(client: AsyncClient):
    """Past the ~7-year record-retention floor: everything left — audio (if
    somehow still present), transcript, note — is gone for good."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    encounter_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_record_days + 1)
    )

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    # Same pass both archives (stage 1) and fully purges (stage 2) an
    # encounter this old.
    assert result.archived == 1
    assert result.purged == 1

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.archived_at is not None
        assert encounter.content_purged_at is not None

        for model in (AudioFile, Transcript, ClinicalNote):
            assert (
                await session.execute(select(model).where(model.encounter_id == encounter_id))
            ).scalar_one_or_none() is None

        audit = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.action == "ENCOUNTER_CONTENT_PURGED", AuditLog.resource_id == str(encounter_id)
                )
            )
        ).scalar_one_or_none()
        assert audit is not None

    # Idempotent: a second sweep finds nothing left to do at all.
    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result_again = await retention_service.run_retention_sweep()
    assert result_again.archived == 0
    assert result_again.purged == 0


async def test_purge_stage_applies_even_to_retain_all_sessions_providers(client: AsyncClient):
    """retain_all_sessions defers the 14-day audio purge, never the 7-year
    regulatory floor — that's a fixed ceiling, not a per-doctor preference."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id, retain_all_sessions=True)
    patient_id = await _make_patient(clinic_id)
    encounter_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_record_days + 1)
    )

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    # Stage 1 is skipped for this provider (retain_all_sessions=True), but
    # stage 2 still fires and cleans up the audio it left behind too.
    assert result.archived == 0
    assert result.purged == 1

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.content_purged_at is not None
        for model in (AudioFile, Transcript, ClinicalNote):
            assert (
                await session.execute(select(model).where(model.encounter_id == encounter_id))
            ).scalar_one_or_none() is None


async def test_purge_stage_skips_encounters_within_the_record_window(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = uuid.UUID(await _new_clinic_id(client, operator["headers"]))
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    # Old enough to archive, nowhere near old enough to fully purge.
    encounter_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_audio_days + 1)
    )

    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        result = await retention_service.run_retention_sweep()
    assert result.archived == 1
    assert result.purged == 0

    async with TestSessionLocal() as session:
        encounter = (await session.execute(select(Encounter).where(Encounter.id == encounter_id))).scalar_one()
        assert encounter.content_purged_at is None
        assert (
            await session.execute(select(Transcript).where(Transcript.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None
        assert (
            await session.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id))
        ).scalar_one_or_none() is not None


# --- GET /encounters?archived filter ----------------------------------------


async def test_list_encounters_excludes_archived_by_default(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    clinic_id = uuid.UUID(provider["clinic_id"])
    provider_id = uuid.UUID(provider["id"])
    patient_id = await _make_patient(clinic_id)

    active_id = await _make_full_encounter(clinic_id, patient_id, provider_id, _days_ago(1))
    archived_id = await _make_full_encounter(
        clinic_id, patient_id, provider_id, _days_ago(settings.retention_audio_days + 1)
    )
    with patch("app.services.retention_service.AsyncSessionLocal", TestSessionLocal):
        await retention_service.run_retention_sweep()

    default_resp = await client.get("/api/v1/encounters", headers=provider["headers"])
    assert default_resp.status_code == 200, default_resp.text
    default_ids = {e["id"] for e in default_resp.json()}
    assert str(active_id) in default_ids
    assert str(archived_id) not in default_ids

    archived_resp = await client.get(
        "/api/v1/encounters", headers=provider["headers"], params={"archived": "true"}
    )
    archived_ids = {e["id"] for e in archived_resp.json()}
    assert str(archived_id) in archived_ids
    assert str(active_id) not in archived_ids
    assert archived_resp.json()[0]["archived_at"] is not None
