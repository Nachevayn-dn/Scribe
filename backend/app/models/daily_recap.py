"""A short, Claude-written recap of a user's week, generated once per
calendar day and cached — see services/daily_recap_service.py."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin


class DailyRecap(UUIDPkMixin, Base):
    __tablename__ = "daily_recaps"
    __table_args__ = (UniqueConstraint("user_id", "recap_date", name="uq_daily_recap_user_date"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Server-local calendar date — same "no per-clinic timezone yet"
    # simplification used elsewhere (e.g. the inbound agent's after-hours
    # window, the outbound reminder scheduler).
    recap_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
