"""The editable, structured clinical note produced by the extraction step."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class NoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SIGNED = "SIGNED"


class EntityType(str, enum.Enum):
    MEDICATION = "MEDICATION"
    PROCEDURE = "PROCEDURE"
    DIAGNOSTIC = "DIAGNOSTIC"
    SYMPTOM = "SYMPTOM"
    ALLERGY = "ALLERGY"


class ClinicalNote(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "clinical_notes"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False, unique=True, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note_templates.id"), nullable=True
    )
    status: Mapped[NoteStatus] = mapped_column(
        Enum(NoteStatus, name="note_status"), default=NoteStatus.DRAFT, nullable=False
    )
    signed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rendered_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_structured: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    entities: Mapped[list["NoteEntity"]] = relationship(
        back_populates="clinical_note", cascade="all, delete-orphan", order_by="NoteEntity.line_index"
    )


class NoteEntity(UUIDPkMixin, Base):
    __tablename__ = "note_entities"

    clinical_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_notes.id"), nullable=False, index=True
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

    clinical_note: Mapped["ClinicalNote"] = relationship(back_populates="entities")
