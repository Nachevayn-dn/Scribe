"""Audio upload -> transcription pipeline, with the OpenAI Whisper call
mocked out so tests never hit the network / need a real API key."""
import asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.services.transcription.base import TranscriptionResult
from tests.conftest import create_user, signup_clinic


async def _start_encounter(client: AsyncClient, admin_headers: dict, provider_headers: dict, provider_id: str) -> str:
    patient_resp = await client.post(
        "/api/v1/patients",
        headers=admin_headers,
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-01"},
    )
    patient_id = patient_resp.json()["id"]
    encounter_resp = await client.post(
        "/api/v1/encounters",
        headers=provider_headers,
        json={"patient_id": patient_id, "provider_id": provider_id},
    )
    assert encounter_resp.status_code == 201, encounter_resp.text
    return encounter_resp.json()["id"]


async def test_audio_upload_runs_pipeline_to_note_ready(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _start_encounter(
        client, admin["headers"], provider["headers"], provider["id"]
    )

    fake_result = TranscriptionResult(
        text="Patient reports tooth pain on the lower left molar.",
        language="en",
        provider_name="openai-whisper-1",
    )

    with patch(
        "app.services.pipeline.OpenAIWhisperProvider"
    ) as mock_provider_cls:
        mock_provider_cls.return_value.transcribe = AsyncMock(return_value=fake_result)

        upload_resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/audio",
            headers=provider["headers"],
            files={"file": ("recording.webm", b"fake-audio-bytes", "audio/webm")},
        )
        assert upload_resp.status_code == 202, upload_resp.text

        # BackgroundTasks run after the response within the same test's event
        # loop (ASGITransport executes them inline before returning control),
        # but give it a beat in case of scheduling differences.
        for _ in range(20):
            status_resp = await client.get(
                f"/api/v1/encounters/{encounter_id}", headers=provider["headers"]
            )
            if status_resp.json()["status"] in ("NOTE_READY", "FAILED"):
                break
            await asyncio.sleep(0.05)

    assert status_resp.json()["status"] == "NOTE_READY", status_resp.json()

    transcript_resp = await client.get(
        f"/api/v1/encounters/{encounter_id}/transcript", headers=provider["headers"]
    )
    assert transcript_resp.status_code == 200
    assert "tooth pain" in transcript_resp.json()["raw_text"]


async def test_audio_upload_marks_failed_on_transcription_error(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _start_encounter(
        client, admin["headers"], provider["headers"], provider["id"]
    )

    with patch("app.services.pipeline.OpenAIWhisperProvider") as mock_provider_cls:
        mock_provider_cls.return_value.transcribe = AsyncMock(
            side_effect=RuntimeError("upstream Whisper API error")
        )

        upload_resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/audio",
            headers=provider["headers"],
            files={"file": ("recording.webm", b"fake-audio-bytes", "audio/webm")},
        )
        assert upload_resp.status_code == 202

        for _ in range(20):
            status_resp = await client.get(
                f"/api/v1/encounters/{encounter_id}", headers=provider["headers"]
            )
            if status_resp.json()["status"] in ("NOTE_READY", "FAILED"):
                break
            await asyncio.sleep(0.05)

    body = status_resp.json()
    assert body["status"] == "FAILED"
    assert "upstream Whisper API error" in body["failure_reason"]
