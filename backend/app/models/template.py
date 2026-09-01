"""Note templates: Clinical Summary, Referral Letter, or a clinic/user-defined custom template."""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class TemplateType(str, enum.Enum):
    CLINICAL_SUMMARY = "CLINICAL_SUMMARY"
    REFERRAL_LETTER = "REFERRAL_LETTER"
    CUSTOM = "CUSTOM"


class NoteTemplate(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "note_templates"

    # NULL clinic_id = a global/system template available to every clinic.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=True, index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[TemplateType] = mapped_column(
        Enum(TemplateType, name="template_type"), nullable=False
    )
    # Ordered list of section names, e.g. ["intake", "diagnostics", "next_steps", "close"]
    structure: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
