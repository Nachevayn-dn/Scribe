"""Appointment — a future patient visit that's been booked but not yet
recorded. Deliberately decoupled from Encounter: an Encounter represents a
scribe session that happened (or is happening) and drives the whole
transcription/note pipeline, while an Appointment is just a booking on the
calendar. Conflating the two would corrupt Encounter.started_at semantics
used throughout the pipeline and the Sessions list."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"


class Appointment(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "appointments"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # The session this follow-up was scheduled from, if any (e.g. booked
    # right after signing a note). Null for appointments booked another way.
    source_encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True
    )
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(lazy="selectin")  # noqa: F821
    provider: Mapped["User"] = relationship(foreign_keys=[provider_id], lazy="selectin")  # noqa: F821
