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
    # Default "from the clinic" identity for shared transcripts/notes.
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Where front-desk/back-office staff want session summaries routed —
    # e.g. to schedule follow-ups or copy into the EHR. Distinct from
    # contact_email since a clinic's public/billing address often isn't
    # the same inbox its staff actually works from.
    staff_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # White-label override: null means "show the default MedicDesk.ai logo
    # and wordmark", which is every clinic's behavior unless a platform
    # admin sets these for a specific clinic (see PLATFORM_ADMIN-gated
    # POST/DELETE /platform/clinics/{id}/logo and the branding_name field
    # on PlatformClinicUpdateRequest). Never editable by a clinic's own
    # SUPER_ADMIN — this is the platform operator's call, not the clinic's.
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    branding_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="clinic", cascade="all, delete-orphan"
    )
