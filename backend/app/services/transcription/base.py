"""Transcription provider interface — MVP ships a single OpenAI Whisper
implementation, but keeping this abstract lets us add providers later
without touching the pipeline."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    provider_name: str


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """language is an optional ISO-639-1 hint (e.g. "bg") — the provider
        the doctor picked when starting the encounter. None lets the
        underlying service auto-detect."""
        raise NotImplementedError
