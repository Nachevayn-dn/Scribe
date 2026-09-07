"""One inbound phone call — the log the doctor's summary widget/page and
the platform's monitoring page both read from."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.agent_common import ContactChannel
from app.models.base import Base, TimestampMixin, UUIDPkMixin


class CallOutcome(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    APPOINTMENT_PROPOSED = "APPOINTMENT_PROPOSED"
    INFO_ONLY = "INFO_ONLY"
    EMERGENCY_ESCALATED = "EMERGENCY_ESCALATED"
    ABANDONED = "ABANDONED"


class InboundCallSession(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "inbound_call_sessions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    twilio_call_sid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    # 30 (not a bare E.164's 20) to fit a "whatsapp:+15550001234" sender.
    from_number: Mapped[str] = mapped_column(String(30), nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    # Set once/if a specific doctor is identified during the call — decides
    # which provider-specific decision rules and doctor preferences apply.
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Twilio hosts the actual recording; we keep a reference, never a copy —
    # played back through an authenticated proxy endpoint, never a raw
    # Twilio URL handed to the browser.
    recording_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    transcript_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    outcome: Mapped[CallOutcome] = mapped_column(
        Enum(CallOutcome, name="call_outcome"), default=CallOutcome.IN_PROGRESS, nullable=False
    )
    proposed_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True
    )
    preferred_contact_channel: Mapped[ContactChannel | None] = mapped_column(
        Enum(ContactChannel, name="call_contact_channel"), nullable=True
    )
    language_used: Mapped[str | None] = mapped_column(String(10), nullable=True)
    summary_shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship(lazy="selectin")  # noqa: F821
    provider: Mapped["User"] = relationship(foreign_keys=[provider_id], lazy="selectin")  # noqa: F821
