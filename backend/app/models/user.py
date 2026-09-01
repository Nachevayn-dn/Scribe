"""User accounts and the Provider<->Assistant many-to-many assignment."""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
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
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

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
