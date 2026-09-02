"""Encounter — anchors a patient visit to a provider and the scribe pipeline."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class EncounterStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    TRANSCRIBING = "TRANSCRIBING"
    # Transcript is ready and shown to the provider; the pipeline stops here
    # deliberately — note generation is a separate, doctor-initiated step
    # (see POST /encounters/{id}/note/generate) rather than automatic.
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    EXTRACTING = "EXTRACTING"
    NOTE_READY = "NOTE_READY"
    SIGNED = "SIGNED"
    FAILED = "FAILED"


class Encounter(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "encounters"

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
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus, name="encounter_status"),
        default=EncounterStatus.IN_PROGRESS,
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ISO-639-1 code (e.g. "en", "bg") chosen by the provider when starting
    # the encounter — the language the visit will be conducted in. Passed
    # through to the transcription provider as a hint (see
    # services/pipeline.py); null means "let Whisper auto-detect."
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship(lazy="selectin")  # noqa: F821
    provider: Mapped["User"] = relationship(foreign_keys=[provider_id], lazy="selectin")  # noqa: F821


class AudioFile(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "audio_files"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
