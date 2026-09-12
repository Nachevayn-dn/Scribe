"""Records that a user clicked "Got it" on an announcement — see
api/announcements.py's POST .../acknowledge. One row per (announcement,
user); its presence is what makes GET /announcements/pending stop returning
that announcement to that user."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPkMixin


class AnnouncementAcknowledgment(UUIDPkMixin, Base):
    __tablename__ = "announcement_acknowledgments"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_ack_user"),
    )

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcements.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
