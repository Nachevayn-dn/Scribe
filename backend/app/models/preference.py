"""Per-doctor preference rules that steer clinical extraction.

E.g. trigger_phrase="tooth pain", instruction="always suggest a CBCT scan".
Kept as simple structured free text (not a rule DSL) — concatenated into the
extraction prompt for the provider's encounters.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class DoctorPreference(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "doctor_preferences"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    trigger_phrase: Mapped[str] = mapped_column(String(500), nullable=False)
    instruction: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
