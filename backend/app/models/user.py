"""User accounts and the Provider<->Assistant many-to-many assignment."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    PROVIDER = "PROVIDER"
    ASSISTANT = "ASSISTANT"


class User(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Null until credentials are generated for this account — see
    # POST /platform/users/{id}/generate-credentials. A platform admin can
    # pre-provision a doctor (create the row, attach it to a clinic) before
    # the doctor has any way to log in; authenticate_user() treats a null
    # hash as "cannot log in", never as "any password works."
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Relative URL (e.g. "/static/avatars/<file>") of an uploaded profile
    # photo — served by the static mount in main.py. Null until the user
    # uploads one (see POST /users/me/photo).
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # UI color scheme, purely a per-viewer preference — "midnight" (dark,
    # amber accent) or "jade" (warm beige, jade-green accent). See
    # frontend/src/styles/global.css.
    theme_preference: Mapped[str] = mapped_column(String(20), default="midnight", nullable=False)
    # Where transcript/note shares should land for this doctor when they
    # choose "send to me" — separate from their login email since it may be
    # a personal inbox rather than the account they log in with.
    notification_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ISO-639-1 code, e.g. "en" — the doctor's default language for new
    # sessions, chosen once on first login after credentials are generated.
    # Null until then; distinct from Encounter.language, which can still be
    # overridden per-visit.
    language_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # True only for MedicDesk operator accounts (not a clinic's own admin) —
    # gates the platform console (see deps.require_platform_admin). There's
    # no self-serve way to become one; it's flagged directly in the DB.
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    clinic: Mapped["Clinic"] = relationship(back_populates="users", lazy="selectin")  # noqa: F821


class ProviderAssistant(UUIDPkMixin, TimestampMixin, Base):
    """Many-to-many: an assistant may support multiple providers (doctors)."""

    __tablename__ = "provider_assistants"
    __table_args__ = (
        UniqueConstraint("provider_id", "assistant_id", name="uq_provider_assistant"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    assistant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    provider: Mapped["User"] = relationship(foreign_keys=[provider_id])
    assistant: Mapped["User"] = relationship(foreign_keys=[assistant_id])
