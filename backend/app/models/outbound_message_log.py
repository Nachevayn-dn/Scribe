"""Audit trail (and source of truth for send-idempotency) for everything
the outbound agent sends — appointment confirmations and pre-procedure
reminders."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.agent_common import ContactChannel
from app.models.base import Base, UUIDPkMixin


class OutboundMessageType(str, enum.Enum):
    APPOINTMENT_CONFIRMATION = "APPOINTMENT_CONFIRMATION"
    REMINDER_DAY_BEFORE = "REMINDER_DAY_BEFORE"
    REMINDER_HOURS_BEFORE = "REMINDER_HOURS_BEFORE"


class OutboundMessageStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"


class OutboundMessageLog(UUIDPkMixin, Base):
    __tablename__ = "outbound_message_logs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    channel: Mapped[ContactChannel] = mapped_column(
        Enum(ContactChannel, name="message_channel"), nullable=False
    )
    message_type: Mapped[OutboundMessageType] = mapped_column(
        Enum(OutboundMessageType, name="outbound_message_type"), nullable=False
    )
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[OutboundMessageStatus] = mapped_column(
        Enum(OutboundMessageStatus, name="outbound_message_status"),
        default=OutboundMessageStatus.SENT,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
