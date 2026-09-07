"""The inbound agent's "decision tree" — an ordered list of independent
condition -> action rules (modular: each one addable/removable/reorderable
on its own), all evaluated together on every call. Clinic-wide by default;
provider_id set overrides/adds to that for one specific doctor."""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class AgentDecisionRule(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "agent_decision_rules"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    # Null = applies to every inbound call at this clinic; set = only calls
    # attributed to this doctor also get this rule.
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    condition: Mapped[str] = mapped_column(String(1000), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
