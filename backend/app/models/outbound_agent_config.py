"""Per-clinic configuration for the outbound reminder agent — when
pre-procedure check-ins go out and on which channels. 1:1 with Clinic."""
import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class OutboundAgentConfig(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "outbound_agent_configs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    day_before_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Local time of day the "day before" reminder goes out.
    day_before_send_hour: Mapped[time] = mapped_column(Time, default=time(10, 0), nullable=False)

    hours_before_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hours_before_offset: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    default_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    additional_languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
