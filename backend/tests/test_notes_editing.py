"""Note edit/sign lifecycle: audit logging, immutability after signing,
and role gating (only the encounter's provider may sign)."""
import asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from tests.conftest import create_user, signup_clinic
from tests.test_pipeline import FAKE_EXTRACTION


async def _ready_encounter(client: AsyncClient, admin_headers: dict, provider: dict) -> str:
    from app.services.transcription.base import TranscriptionResult

    patient_resp = await client.post(
        "/api/v1/patients",
        headers=admin_headers,
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-01"},
    )
    patient_id = patient_resp.json()["id"]
    encounter_resp = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    encounter_id = encounter_resp.json()["id"]

    fake_transcript = TranscriptionResult(
        text="Patient reports tooth pain.", language="en", provider_name="openai-whisper-1"
    )
    with patch("app.services.pipeline.OpenAIWhisperProvider") as mock_whisper_cls:
        mock_whisper_cls.return_value.transcribe = AsyncMock(return_value=fake_transcript)

        await client.post(
            f"/api/v1/encounters/{encounter_id}/audio",
            headers=provider["headers"],
            files={"file": ("recording.webm", b"fake-audio-bytes", "audio/webm")},
        )
        for _ in range(20):
            status_resp = await client.get(
                f"/api/v1/encounters/{encounter_id}", headers=provider["headers"]
            )
            if status_resp.json()["status"] in ("TRANSCRIPT_READY", "FAILED"):
                break
            await asyncio.sleep(0.05)
    assert status_resp.json()["status"] == "TRANSCRIPT_READY", status_resp.json()

    templates_resp = await client.get("/api/v1/templates", headers=provider["headers"])
    template_id = next(
        t["id"] for t in templates_resp.json() if t["template_type"] == "CLINICAL_SUMMARY"
    )

    with patch("app.services.extraction_step.AnthropicExtractionProvider") as mock_claude_cls:
        mock_claude_cls.return_value.extract = AsyncMock(return_value=FAKE_EXTRACTION)
        generate_resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/note/generate",
            headers=provider["headers"],
            params={"template_id": template_id},
        )
    assert generate_resp.status_code == 200, generate_resp.text
    return encounter_id


async def test_edit_note_writes_audit_log_and_marks_entity_edited(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    resp = await client.patch(
        f"/api/v1/encounters/{encounter_id}/note",
        headers=provider["headers"],
        json={"line_index": 1, "new_text": "Patient reports severe tooth pain."},
    )
    assert resp.status_code == 200, resp.text
    note = resp.json()
    assert "severe tooth pain" in note["rendered_content"]
    edited_entities = [e for e in note["entities"] if e["line_index"] == 1]
    assert all(e["is_edited"] for e in edited_entities)

    audit_resp = await client.get(
        "/api/v1/audit-log", headers=admin["headers"], params={"resource_type": "ClinicalNote"}
    )
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "NOTE_EDITED" in actions


async def test_only_provider_can_sign_note(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")
    await client.post(
        f"/api/v1/users/{provider['id']}/assistants/{assistant['id']}", headers=admin["headers"]
    )
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    forbidden = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=assistant["headers"]
    )
    assert forbidden.status_code == 403

    forbidden_admin = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=admin["headers"]
    )
    assert forbidden_admin.status_code == 403

    resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=provider["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SIGNED"


async def test_signed_note_is_immutable(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    sign_resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=provider["headers"]
    )
    assert sign_resp.status_code == 200

    edit_resp = await client.patch(
        f"/api/v1/encounters/{encounter_id}/note",
        headers=provider["headers"],
        json={"line_index": 0, "new_text": "Should not be allowed"},
    )
    assert edit_resp.status_code == 409

    sign_again_resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=provider["headers"]
    )
    assert sign_again_resp.status_code == 409
