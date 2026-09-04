"""Documents a platform admin attaches to a clinic during onboarding — the
signed contract, the order form, and (potentially several) consent-form
templates. English only for now; doc_type stays generic so other document
kinds can be added later without a new table."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin


class ClinicDocumentType(str, enum.Enum):
    CONTRACT = "CONTRACT"
    ORDER_FORM = "ORDER_FORM"
    CONSENT_FORM = "CONSENT_FORM"


class ClinicDocument(UUIDPkMixin, Base):
    __tablename__ = "clinic_documents"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    doc_type: Mapped[ClinicDocumentType] = mapped_column(
        Enum(ClinicDocumentType, name="clinic_document_type"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
