"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://scribe:scribe@localhost:5432/scribe"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12  # 12 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # External providers
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    # Only needed if your Anthropic API key is a "multi-workspace" personal
    # key (Anthropic returns a 400 asking for this if so). Not a secret —
    # find it at console.anthropic.com/settings/workspaces.
    anthropic_workspace_id: str | None = None
    whisper_model: str = "whisper-1"
    anthropic_model: str = "claude-sonnet-5"

    # Storage
    audio_storage_dir: str = "./data/audio"


@lru_cache
def get_settings() -> Settings:
    return Settings()
