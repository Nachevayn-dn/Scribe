"""Transcript entity tagging (lazy, cached on first view) and per-line
transcript editing, with the Claude tagging call mocked out."""
import asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.services.extraction.base import TaggedLine, TaggingResult
from app.services.transcription.base import TranscriptionResult
from tests.conftest import create_user, signup_clinic

FAKE_TAGGING = TaggingResult(
    lines=[
        TaggedLine(
            line_index=1,
            entities=[
                {
                    "entity_type": "SYMPTOM",
                    "text": "tooth pain",
                    "start_offset": 15,
                    "end_offset": 25,
                }
            ],
        )
    ]
)


async def _transcript_ready_encounter(
    client: AsyncClient, admin_headers: dict, provider: dict
) -> str:
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

    fake_result = TranscriptionResult(
        text="Chief complaint noted. Patient reports tooth pain on the lower left molar.",
        language="en",
        provider_name="openai-whisper-1",
    )
    with patch("app.services.pipeline.OpenAIWhisperProvider") as mock_whisper_cls:
        mock_whisper_cls.return_value.transcribe = AsyncMock(return_value=fake_result)
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
    return encounter_id


async def test_transcript_is_tagged_lazily_on_first_view(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _transcript_ready_encounter(client, admin["headers"], provider)

    with patch("app.services.transcript_tagging.AnthropicExtractionProvider") as mock_cls:
        tag_mock = AsyncMock(return_value=FAKE_TAGGING)
        mock_cls.return_value.tag_lines = tag_mock

        first_resp = await client.get(
            f"/api/v1/encounters/{encounter_id}/transcript", headers=provider["headers"]
        )
        assert first_resp.status_code == 200, first_resp.text
        entities = first_resp.json()["entities"]
        assert len(entities) == 1
        assert entities[0]["entity_type"] == "SYMPTOM"
        assert entities[0]["text"] == "tooth pain"
        tag_mock.assert_awaited_once()

        # Second view must not re-tag (already-present entities short-circuit).
        second_resp = await client.get(
            f"/api/v1/encounters/{encounter_id}/transcript", headers=provider["headers"]
        )
        assert second_resp.status_code == 200
        assert len(second_resp.json()["entities"]) == 1
        tag_mock.assert_awaited_once()


async def test_transcript_view_survives_tagging_failure(client: AsyncClient):
    """No ANTHROPIC_API_KEY / a transient Claude error must not break the
    transcript view — it just comes back without highlighting."""
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _transcript_ready_encounter(client, admin["headers"], provider)

    with patch("app.services.transcript_tagging.AnthropicExtractionProvider") as mock_cls:
        mock_cls.side_effect = RuntimeError("ANTHROPIC_API_KEY is not set")
        resp = await client.get(
            f"/api/v1/encounters/{encounter_id}/transcript", headers=provider["headers"]
        )
    assert resp.status_code == 200
    assert resp.json()["entities"] == []


async def test_edit_transcript_line_updates_text_and_marks_entity_edited(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _transcript_ready_encounter(client, admin["headers"], provider)

    with patch("app.services.transcript_tagging.AnthropicExtractionProvider") as mock_cls:
        mock_cls.return_value.tag_lines = AsyncMock(return_value=FAKE_TAGGING)
        await client.get(
            f"/api/v1/encounters/{encounter_id}/transcript", headers=provider["headers"]
        )

    edit_resp = await client.patch(
        f"/api/v1/encounters/{encounter_id}/transcript",
        headers=provider["headers"],
        json={"line_index": 1, "new_text": "Patient reports severe tooth pain."},
    )
    assert edit_resp.status_code == 200, edit_resp.text
    body = edit_resp.json()
    assert "severe tooth pain" in body["raw_text"].split("\n")[1]
    edited = [e for e in body["entities"] if e["line_index"] == 1]
    assert edited and all(e["is_edited"] for e in edited)

    audit_resp = await client.get(
        "/api/v1/audit-log", headers=admin["headers"], params={"resource_type": "Transcript"}
    )
    assert audit_resp.status_code == 200
    assert "TRANSCRIPT_EDITED" in [a["action"] for a in audit_resp.json()]


async def test_edit_transcript_rejects_out_of_range_line(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _transcript_ready_encounter(client, admin["headers"], provider)

    resp = await client.patch(
        f"/api/v1/encounters/{encounter_id}/transcript",
        headers=provider["headers"],
        json={"line_index": 99, "new_text": "no such line"},
    )
    assert resp.status_code == 404
