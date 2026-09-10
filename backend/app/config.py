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

    # Outgoing email (sharing transcripts/notes) via Resend.
    # console.resend.com — free tier, no domain required to start: leave
    # resend_from_email unset and it falls back to Resend's shared
    # onboarding@resend.dev sender (fine for testing; verify your own domain
    # in Resend before relying on this for real patient communication).
    resend_api_key: str | None = None
    resend_from_email: str = "MedicDesk.ai <onboarding@resend.dev>"

    # Inbound/outbound agents — phone, SMS, WhatsApp via Twilio
    # (console.twilio.com). Buying a phone number and sending
    # SMS/WhatsApp/voice minutes are real, billed usage on your Twilio
    # account — not free like Resend's tier. twilio_whatsapp_from defaults
    # to Twilio's shared sandbox sender; swap in your own Meta-verified
    # WhatsApp Business number here once approved, no code changes needed.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    # The publicly reachable base URL Twilio should call back to for voice/
    # SMS/WhatsApp webhooks (e.g. your ngrok URL while testing, or your real
    # deployment's URL once live). Required before "Generate phone number"
    # can wire up webhooks — without it a number can still be purchased but
    # won't route calls anywhere useful.
    public_base_url: str | None = None

    # Optional: swaps the inbound agent's Twilio <Say> voice (robotic) for
    # a natural ElevenLabs one (elevenlabs.io/app/settings/api-keys). Falls
    # back to Twilio's own voice automatically when not set — this is a
    # pure upgrade, not required. Twilio's own speech recognition (hearing
    # the caller) is unaffected either way. elevenlabs_voice_id defaults to
    # "Rachel", one of ElevenLabs' premade voices; pick a different one at
    # elevenlabs.io/app/voice-library and swap the ID here, no code change.
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # The base URL of the *frontend* app (not public_base_url above, which
    # is the backend's own webhook URL for Twilio) — used to build the
    # "set your password" link emailed to a newly-provisioned doctor (see
    # POST /platform/users/{id}/send-setup-link). Defaults to the local dev
    # server; set this to your real domain (e.g. https://medicdesk.ai) once
    # deployed so the emailed link actually reaches the recipient.
    frontend_base_url: str = "http://localhost:5173"

    # Storage
    audio_storage_dir: str = "./data/audio"
    avatar_storage_dir: str = "./data/avatars"
    # Clinic contracts/order forms/consent forms — private, never served
    # from a public URL (see services/document_storage.py).
    document_storage_dir: str = "./data/documents"

    # Data retention (see services/retention_service.py) — two stages:
    # audio is deleted and the session archived after retention_audio_days
    # (skippable per-doctor via User.retain_all_sessions, once a signed
    # consent is on file); the transcript and clinical note — the actual
    # medical record — are kept until retention_record_days regardless of
    # that override, then purged too. ~7 years (2,555 days) is a common
    # minimum medical-record-retention period; confirm the exact figure for
    # your jurisdiction before relying on it.
    retention_audio_days: int = 14
    retention_record_days: int = 2555


@lru_cache
def get_settings() -> Settings:
    return Settings()
