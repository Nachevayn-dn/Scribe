"""Platform-wide announcement video storage — same local-disk pattern as
services/document_storage.py (kept separate since these are keyed by
announcement id, not clinic id: an announcement can target every clinic at
once). Never served from a public URL — only through an authenticated
streaming endpoint (see api/announcements.py)."""
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


async def save_announcement_video(announcement_id: uuid.UUID, content: bytes, original_filename: str) -> str:
    directory = Path(settings.announcement_storage_dir) / str(announcement_id)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix[:10]
    filename = f"{uuid.uuid4()}{suffix}"
    path = directory / filename
    path.write_bytes(content)
    return str(path)


def read_announcement_video(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
