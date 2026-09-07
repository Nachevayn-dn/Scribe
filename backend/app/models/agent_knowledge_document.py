"""The inbound/outbound agents' reference-material repository — services,
prices, Q&A, procedure instructions, uploaded by the platform admin per
clinic. A sibling to ClinicDocument (contracts/consent forms), not a reuse
of it: this needs a title, an agent-type split, and extracted text for
prompting, and it's meant to grow and be replaced over time rather than
being an append-only onboarding record."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.agent_common import AgentType
from app.models.base import Base, UUIDPkMixin


class AgentKnowledgeDocument(UUIDPkMixin, Base):
    __tablename__ = "agent_knowledge_documents"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType, name="agent_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Plain text pulled out at upload time (PDF/docx/txt) so it can go
    # straight into a Claude prompt without re-parsing on every call turn.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def has_extracted_text(self) -> bool:
        """Whether prompt-ready text was pulled out at upload time — the
        raw extracted_text itself is never serialized to the API (list
        responses would balloon), just this flag."""
        return bool(self.extracted_text)
