"""Per-clinic configuration for the inbound phone/WhatsApp agent — the
Twilio connection, when it picks up, what language(s) it speaks, and how
call summaries get shared. 1:1 with Clinic."""
import enum
import uuid
from datetime import time

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.agent_common import ContactChannel
from app.models.base import Base, TimestampMixin, UUIDPkMixin


class PickupMode(str, enum.Enum):
    # The agent answers every call directly — the Twilio number IS the
    # clinic's line.
    ALWAYS = "ALWAYS"
    # The agent only answers outside business hours (after_hours_start ->
    # after_hours_end); otherwise calls forward to forward_to_number.
    AFTER_HOURS = "AFTER_HOURS"
    # Calls ring forward_to_number first; the agent only picks up if
    # unanswered after no_answer_timeout_seconds.
    NO_ANSWER = "NO_ANSWER"


class SummaryShareWith(str, enum.Enum):
    DOCTOR_ONLY = "DOCTOR_ONLY"
    TEAM = "TEAM"


class InboundAgentConfig(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "inbound_agent_configs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # E.164 number Twilio provisioned for this clinic, and Twilio's SID for
    # it (needed to update its webhook URLs later).
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_number_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # A Twilio WhatsApp-enabled sender — the shared sandbox code
    # ("whatsapp:+14155238886") until a Meta-verified business number
    # replaces it; no code change needed when that happens.
    whatsapp_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    default_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    # ISO-639-1 codes the agent can also converse in, chosen at call time
    # from the caller's stated preference.
    additional_languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    greeting_text: Mapped[str] = mapped_column(
        String(1000),
        default="Thank you for calling. How can I help you today?",
        nullable=False,
    )

    pickup_mode: Mapped[PickupMode] = mapped_column(
        Enum(PickupMode, name="agent_pickup_mode"), default=PickupMode.ALWAYS, nullable=False
    )
    after_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    after_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    no_answer_timeout_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # The clinic's existing real phone line — where calls forward to/ring
    # first under AFTER_HOURS/NO_ANSWER modes.
    forward_to_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    recording_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    share_summary_with: Mapped[SummaryShareWith] = mapped_column(
        Enum(SummaryShareWith, name="summary_share_with"),
        default=SummaryShareWith.DOCTOR_ONLY,
        nullable=False,
    )
    # Distinct Postgres enum name from other ContactChannel columns
    # (InboundCallSession, OutboundMessageLog) — same Python enum reused for
    # its value set, but hand-written migrations create one Postgres type
    # per column here rather than sharing, to avoid CREATE TYPE collisions.
    share_channel: Mapped[ContactChannel] = mapped_column(
        Enum(ContactChannel, name="agent_share_channel"), default=ContactChannel.EMAIL, nullable=False
    )
