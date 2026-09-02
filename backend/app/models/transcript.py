"""The transcript produced by the transcription provider.

raw_text is line-split at persist time (one sentence-ish line per "\n",
same convention as ClinicalNote.rendered_content) so the doctor can review
and correct individual lines before generating a note from them — see
TranscriptEntity for the per-line entity highlighting shown alongside it.
"""
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin
from app.models.clinical_note import EntityType


class Transcript(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "transcripts"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)

    entities: Mapped[list["TranscriptEntity"]] = relationship(
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptEntity.line_index",
        lazy="selectin",
    )


class TranscriptEntity(UUIDPkMixin, Base):
    """Entity tags on the raw transcript, mirroring NoteEntity — tagged
    lazily (once) the first time a transcript is viewed, not automatically
    during the upload pipeline, to avoid an extra Claude call on every
    recording regardless of whether anyone reviews it."""

    __tablename__ = "transcript_entities"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=False, index=True
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    transcript: Mapped["Transcript"] = relationship(back_populates="entities")
