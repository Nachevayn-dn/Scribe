"""A platform-admin broadcast to doctors/users — a message and an optional
video, shown as a must-acknowledge popup in the app (see api/announcements.py
and models/announcement_acknowledgment.py)."""
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Announcement(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "announcements"

    # Null = every clinic on the platform; set = just this one.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=True, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    video_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    video_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    video_original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # A platform admin can retire an announcement (stop showing it to anyone
    # who hasn't seen it yet) without deleting the row/history.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
