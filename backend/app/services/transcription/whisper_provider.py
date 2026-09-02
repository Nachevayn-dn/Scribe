"""Real OpenAI Whisper transcription (audio/transcriptions endpoint)."""
import io

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.transcription.base import TranscriptionProvider, TranscriptionResult

settings = get_settings()


class OpenAIWhisperProvider(TranscriptionProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set — required for audio transcription"
            )
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename  # the SDK reads this for multipart form filename
        kwargs = {"language": language} if language else {}
        response = await self._client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=audio_file,
            **kwargs,
        )
        return TranscriptionResult(
            text=response.text,
            language=getattr(response, "language", None),
            provider_name=f"openai-{settings.whisper_model}",
        )
