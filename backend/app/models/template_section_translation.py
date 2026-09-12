"""A doctor-confirmed translation of one template's section titles into one
language — e.g. NoteTemplate("Clinical Summary").structure is English
("Intake", "Diagnostics", ...); this row holds the Hungarian equivalents
once a doctor has reviewed and saved them. Looked up automatically by
services/extraction_step.py whenever a session's language isn't English, so
every future session in that language with that template renders its
headers correctly without asking again."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin


class TemplateSectionTranslation(UUIDPkMixin, Base):
    __tablename__ = "template_section_translations"
    __table_args__ = (
        UniqueConstraint("template_id", "language", name="uq_template_translation_language"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note_templates.id"), nullable=False, index=True
    )
    # ISO-639-1 code, e.g. "hu", "bg" — never "en" (the template's own
    # structure already is the English version).
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    # Same order/length as the template's structure, translated.
    translated_structure: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confirmed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
