"""Covers the "batch of doctor-requested changes" feature set: the cached
daily dashboard recap, per-template section-title translations (confirm +
automatic reuse at extraction time), the "share with patient" letter +
history, and platform-wide must-acknowledge announcements."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from app.models.clinic import Clinic
from app.models.daily_recap import DailyRecap
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.transcript import Transcript
from app.models.user import User, UserRole
from tests.conftest import TestSessionLocal, create_user, signup_clinic
from tests.test_pipeline import FAKE_EXTRACTION


async def _make_platform_admin(email: str) -> None:
    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_platform_admin = True
        await session.commit()


# --- Daily recap -------------------------------------------------------------


async def test_daily_recap_is_cached_per_day(client: AsyncClient):
    admin = await signup_clinic(client)

    with patch("app.services.daily_recap_service._write_recap_text", AsyncMock(return_value="Quiet week.")):
        first = await client.get("/api/v1/dashboard/recap", headers=admin["headers"])
        second = await client.get("/api/v1/dashboard/recap", headers=admin["headers"])

    assert first.status_code == 200, first.text
    assert first.json()["summary_text"] == "Quiet week."
    assert second.json() == first.json()

    me = await client.get("/api/v1/auth/me", headers=admin["headers"])
    async with TestSessionLocal() as session:
        rows = (
            await session.execute(select(DailyRecap).where(DailyRecap.user_id == uuid.UUID(me.json()["id"])))
        ).scalars().all()
        assert len(rows) == 1  # second GET was served from cache, not a second Claude call/row


# --- Template section translations ------------------------------------------


async def _create_custom_template(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "Insurance Note", "template_type": "CUSTOM", "structure": ["Chief Complaint", "Diagnosis Codes"]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_translation_draft_then_confirm_is_reused(client: AsyncClient):
    admin = await signup_clinic(client)
    template_id = await _create_custom_template(client, admin["headers"])

    with patch(
        "app.services.section_translation_service.draft_section_translation",
        AsyncMock(return_value=["Panasz", "Diagnózis kódok"]),
    ):
        draft_resp = await client.get(
            f"/api/v1/templates/{template_id}/translations/hu", headers=admin["headers"]
        )
    assert draft_resp.status_code == 200, draft_resp.text
    assert draft_resp.json()["is_confirmed"] is False
    assert draft_resp.json()["translated_structure"] == ["Panasz", "Diagnózis kódok"]

    confirm_resp = await client.put(
        f"/api/v1/templates/{template_id}/translations/hu",
        headers=admin["headers"],
        json={"translated_structure": ["Panasz (edited)", "Diagnózis kódok"]},
    )
    assert confirm_resp.status_code == 200, confirm_resp.text

    reload_resp = await client.get(
        f"/api/v1/templates/{template_id}/translations/hu", headers=admin["headers"]
    )
    assert reload_resp.json()["is_confirmed"] is True
    assert reload_resp.json()["translated_structure"] == ["Panasz (edited)", "Diagnózis kódok"]


async def test_assistant_cannot_confirm_translation(client: AsyncClient):
    admin = await signup_clinic(client)
    template_id = await _create_custom_template(client, admin["headers"])
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")

    resp = await client.put(
        f"/api/v1/templates/{template_id}/translations/hu",
        headers=assistant["headers"],
        json={"translated_structure": ["x", "y"]},
    )
    assert resp.status_code == 403


async def test_extraction_uses_confirmed_translation_for_visit_language(client: AsyncClient):
    from app.services.extraction_step import run_extraction

    admin = await signup_clinic(client)
    template_id = await _create_custom_template(client, admin["headers"])
    await client.put(
        f"/api/v1/templates/{template_id}/translations/hu",
        headers=admin["headers"],
        json={"translated_structure": ["Panasz", "Diagnózis kódok"]},
    )

    async with TestSessionLocal() as db:
        clinic_id = (await db.execute(select(Clinic))).scalars().first().id
        provider = (
            await db.execute(select(User).where(User.clinic_id == clinic_id, User.role == UserRole.SUPER_ADMIN))
        ).scalars().first()
        patient = Patient(clinic_id=clinic_id, first_name="A", last_name="B", date_of_birth=date(1990, 1, 1))
        db.add(patient)
        await db.flush()
        encounter = Encounter(
            clinic_id=clinic_id, patient_id=patient.id, provider_id=provider.id,
            created_by_id=provider.id, language="hu",
        )
        db.add(encounter)
        await db.flush()
        transcript = Transcript(encounter_id=encounter.id, raw_text="Fogfájás.", provider="whisper")
        db.add(transcript)
        await db.commit()
        await db.refresh(encounter)
        await db.refresh(transcript)

        with patch("app.services.extraction_step.AnthropicExtractionProvider") as mock_claude_cls:
            extract_mock = AsyncMock(return_value=FAKE_EXTRACTION)
            mock_claude_cls.return_value.extract = extract_mock
            await run_extraction(db, encounter, transcript, template_id=uuid.UUID(template_id))

        extract_mock.assert_awaited_once()
        _, _, _, section_titles_override = extract_mock.await_args.args
        assert section_titles_override == ["Panasz", "Diagnózis kódok"]


# --- Share with patient -------------------------------------------------------


async def _note_ready_encounter_with_patient_email(client: AsyncClient, admin_headers: dict, provider: dict, email: str | None) -> str:
    patient_resp = await client.post(
        "/api/v1/patients",
        headers=admin_headers,
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-01", "email": email},
    )
    patient_id = patient_resp.json()["id"]
    encounter_resp = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    encounter_id = encounter_resp.json()["id"]

    async with TestSessionLocal() as db:
        transcript = Transcript(
            encounter_id=uuid.UUID(encounter_id), raw_text="Patient reports tooth pain.", provider="whisper"
        )
        db.add(transcript)
        await db.commit()

    templates_resp = await client.get("/api/v1/templates", headers=provider["headers"])
    template_id = next(t["id"] for t in templates_resp.json() if t["template_type"] == "CLINICAL_SUMMARY")

    with patch("app.services.extraction_step.AnthropicExtractionProvider") as mock_claude_cls:
        mock_claude_cls.return_value.extract = AsyncMock(return_value=FAKE_EXTRACTION)
        generate_resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/note/generate",
            headers=provider["headers"],
            params={"template_id": template_id},
        )
    assert generate_resp.status_code == 200, generate_resp.text
    return encounter_id


async def test_share_with_patient_requires_email_on_file(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _note_ready_encounter_with_patient_email(client, admin["headers"], provider, None)

    resp = await client.post(f"/api/v1/encounters/{encounter_id}/share-with-patient", headers=provider["headers"])
    assert resp.status_code == 400


async def test_share_with_patient_sends_letter_and_logs_it(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _note_ready_encounter_with_patient_email(
        client, admin["headers"], provider, "jane@example.com"
    )

    with patch("app.api.notes.send_share_email", return_value="msg_123") as mock_send:
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/share-with-patient", headers=provider["headers"]
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["recipient"] == "jane@example.com"
    mock_send.assert_called_once()
    body_text = mock_send.call_args.kwargs["body_text"]
    assert body_text.startswith("Dear Jane,")
    assert body_text.rstrip().endswith(provider["full_name"])

    history_resp = await client.get(
        f"/api/v1/encounters/{encounter_id}/patient-shares", headers=provider["headers"]
    )
    assert history_resp.status_code == 200, history_resp.text
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["recipient_email"] == "jane@example.com"


# --- Platform-wide announcements ---------------------------------------------


async def test_announcement_targeting_all_vs_one_clinic(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    clinic_a = (
        await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Clinic A"})
    ).json()
    clinic_b = (
        await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Clinic B"})
    ).json()

    everyone = await client.post(
        "/api/v1/platform/announcements",
        headers=operator["headers"],
        data={"message": "Platform maintenance tonight."},
    )
    assert everyone.status_code == 201, everyone.text

    just_a = await client.post(
        "/api/v1/platform/announcements",
        headers=operator["headers"],
        data={"message": "Clinic A only update.", "clinic_id": clinic_a["id"]},
    )
    assert just_a.status_code == 201, just_a.text

    just_b = await client.post(
        "/api/v1/platform/announcements",
        headers=operator["headers"],
        data={"message": "Clinic B only update.", "clinic_id": clinic_b["id"]},
    )
    assert just_b.status_code == 201, just_b.text

    doctor_a = await client.post(
        f"/api/v1/platform/clinics/{clinic_a['id']}/doctors",
        headers=operator["headers"],
        json={"email": f"doc-a-{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dr. A"},
    )
    async with TestSessionLocal() as db:
        from app.core.security import hash_password

        user_id = doctor_a.json()["id"]
        user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalar_one()
        user.hashed_password = hash_password("supersecret1")
        await db.commit()

    login = await client.post(
        "/api/v1/auth/login", json={"email": doctor_a.json()["email"], "password": "supersecret1"}
    )
    doctor_a_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    pending = await client.get("/api/v1/announcements/pending", headers=doctor_a_headers)
    assert pending.status_code == 200, pending.text
    messages = {a["message"] for a in pending.json()}
    assert "Platform maintenance tonight." in messages
    assert "Clinic A only update." in messages
    assert "Clinic B only update." not in messages


async def test_announcement_acknowledge_is_idempotent_and_removes_from_pending(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    created = await client.post(
        "/api/v1/platform/announcements", headers=operator["headers"], data={"message": "Hello everyone."}
    )
    announcement_id = created.json()["id"]

    before = await client.get("/api/v1/announcements/pending", headers=operator["headers"])
    assert any(a["id"] == announcement_id for a in before.json())

    ack1 = await client.post(f"/api/v1/announcements/{announcement_id}/acknowledge", headers=operator["headers"])
    ack2 = await client.post(f"/api/v1/announcements/{announcement_id}/acknowledge", headers=operator["headers"])
    assert ack1.status_code == 204
    assert ack2.status_code == 204  # idempotent, no error on a repeat ack

    after = await client.get("/api/v1/announcements/pending", headers=operator["headers"])
    assert not any(a["id"] == announcement_id for a in after.json())


async def test_deactivated_announcement_disappears_from_pending(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    created = await client.post(
        "/api/v1/platform/announcements", headers=operator["headers"], data={"message": "Retire me."}
    )
    announcement_id = created.json()["id"]

    del_resp = await client.delete(f"/api/v1/platform/announcements/{announcement_id}", headers=operator["headers"])
    assert del_resp.status_code == 204

    pending = await client.get("/api/v1/announcements/pending", headers=operator["headers"])
    assert not any(a["id"] == announcement_id for a in pending.json())
