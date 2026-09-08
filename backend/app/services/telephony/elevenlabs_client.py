"""ElevenLabs text-to-speech — swaps Twilio's built-in robotic <Say> voice
for a natural one, without touching anything else about the inbound
agent: Twilio's own speech recognition (hearing the caller) is unchanged,
the turn-based webhook flow is unchanged, Claude's decision-making is
unchanged. See api/telephony.py's _speak() for how this plugs in — it
falls back to Twilio's own <Say> automatically when this isn't
configured, exactly like every other optional integration in this app.
"""
import logging

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsNotConfiguredError(RuntimeError):
    pass


async def synthesize_speech(text: str) -> bytes:
    """Returns MP3 audio bytes for the given text. Uses ElevenLabs'
    multilingual model, which infers pronunciation directly from the
    text — no separate language code to pass, unlike Twilio's <Say>."""
    if not settings.elevenlabs_api_key:
        raise ElevenLabsNotConfiguredError(
            "ElevenLabs isn't set up yet — add ELEVENLABS_API_KEY to use a natural voice "
            "instead of Twilio's default."
        )

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(
                f"{_API_BASE}/text-to-speech/{settings.elevenlabs_voice_id}",
                headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception("ElevenLabs TTS request failed")
            raise RuntimeError(
                f"ElevenLabs TTS failed: {exc.response.status_code} {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("ElevenLabs TTS request failed")
            raise RuntimeError(f"ElevenLabs TTS failed: {exc}") from exc

    return response.content
