"""Clinic (practice) — the top-level multi-tenant entity.

Kept deliberately generic (not scribe-specific) so future agent types
(inbound/outbound call agents) can be hosted under the same tenant model.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class Clinic(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="clinic", cascade="all, delete-orphan"
    )
