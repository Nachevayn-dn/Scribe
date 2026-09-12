"""White-label clinic logo storage — same local-disk, served-over-HTTP
pattern as services/avatar_storage.py, kept separate since these live under
their own /static mount and their own storage directory.
"""
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()

_EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}


def save_clinic_logo(clinic_id: uuid.UUID, content: bytes, mime_type: str) -> str:
    """Persists the image and returns its public URL (relative — served via
    the /static/clinic-logos mount, proxied through the frontend's own
    origin in both dev and prod, same as avatar_storage.save_avatar)."""
    extension = _EXTENSION_BY_MIME.get(mime_type)
    if extension is None:
        raise ValueError(f"Unsupported image type: {mime_type}")

    directory = Path(settings.clinic_logo_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{clinic_id}-{uuid.uuid4().hex[:8]}.{extension}"
    (directory / filename).write_bytes(content)
    return f"/static/clinic-logos/{filename}"
