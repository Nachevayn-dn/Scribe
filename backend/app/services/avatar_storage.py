"""Doctor profile-photo storage — same local-disk pattern as services/storage.py
(audio), kept separate since avatars are served back over HTTP (see the
static mount in main.py) while audio never is.
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
    "image/gif": "gif",
}


def save_avatar(user_id: uuid.UUID, content: bytes, mime_type: str) -> str:
    """Persists the image and returns its public URL (relative — served via
    the /static/avatars mount, proxied through the frontend's own origin in
    both dev and prod so it never needs to know the backend's absolute host)."""
    extension = _EXTENSION_BY_MIME.get(mime_type)
    if extension is None:
        raise ValueError(f"Unsupported image type: {mime_type}")

    directory = Path(settings.avatar_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}.{extension}"
    (directory / filename).write_bytes(content)
    return f"/static/avatars/{filename}"
