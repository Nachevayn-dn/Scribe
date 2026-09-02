from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Healthcare AI Platform — Scribe Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Serves uploaded doctor profile photos (see services/avatar_storage.py).
# Proxied through the frontend's own origin in dev (vite.config.ts) and prod
# (nginx.conf) so photo_url stays a host-agnostic relative path.
_avatar_dir = Path(settings.avatar_storage_dir)
_avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=_avatar_dir), name="avatars")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
