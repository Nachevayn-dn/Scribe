"""Clinic document storage (contracts, order forms, consent forms) — same
local-disk pattern as services/storage.py (audio), kept separate on purpose:
unlike avatars, these are sensitive and are never served from a public URL.
They're only ever read back through an authenticated, platform-admin-gated
streaming download endpoint (see api/platform.py)."""
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


async def save_document(clinic_id: uuid.UUID, content: bytes, original_filename: str) -> str:
    """Persists document bytes to disk and returns the storage path."""
    directory = Path(settings.document_storage_dir) / str(clinic_id)
    directory.mkdir(parents=True, exist_ok=True)
    # Keep the original extension (if any) for a sane download filename
    # later, but never trust the original name itself as a path component.
    suffix = Path(original_filename).suffix[:10]
    filename = f"{uuid.uuid4()}{suffix}"
    path = directory / filename
    path.write_bytes(content)
    return str(path)


def read_document(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
