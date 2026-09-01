"""Audio file storage abstraction.

MVP implementation stores files on local disk under AUDIO_STORAGE_DIR. Kept
behind a narrow interface so a later swap to S3 (or similar) only touches
this module.
"""
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()

_EXTENSION_BY_MIME = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/ogg": "ogg",
}


def _extension_for(mime_type: str) -> str:
    return _EXTENSION_BY_MIME.get(mime_type, "bin")


async def save_audio(encounter_id: uuid.UUID, content: bytes, mime_type: str) -> str:
    """Persists audio bytes to disk and returns the storage path (relative)."""
    directory = Path(settings.audio_storage_dir) / str(encounter_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.{_extension_for(mime_type)}"
    path = directory / filename
    path.write_bytes(content)
    return str(path)


def read_audio(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
