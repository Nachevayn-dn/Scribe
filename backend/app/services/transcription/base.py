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
    async def transcribe(self, audio_bytes: bytes, mime_type: str, filename: str) -> TranscriptionResult:
        raise NotImplementedError
