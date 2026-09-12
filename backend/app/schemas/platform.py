import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.clinic_document import ClinicDocumentType
from app.models.user import UserRole


class PlatformClinicCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
    # Optional at creation time so a platform admin can set these up front
    # (and see them echoed back in the creation confirmation) instead of
    # having to visit the clinic's Details tab as a separate step.
    contact_email: EmailStr | None = None
    staff_email: EmailStr | None = None


class PlatformClinicUpdateRequest(BaseModel):
    """Partial update — every field optional, only what's set gets changed.
    Lets the platform admin manage a clinic's own contact/staff email
    independently of whichever account they're logged in as (previously
    only editable via the clinic's own /settings page, which always
    acts on the logged-in user's own clinic)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
    contact_email: EmailStr | None = None
    staff_email: EmailStr | None = None
    is_active: bool | None = None
    # White-label override — the text shown instead of "MedicDesk.ai" for
    # this clinic's own users. Send null explicitly to revert to the
    # default; omit the field entirely to leave it unchanged (same
    # exclude_unset semantics as every other field here). The logo image
    # itself is a separate upload — see POST/DELETE /platform/clinics/{id}/logo.
    branding_name: str | None = Field(default=None, max_length=255)


class PlatformClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_active: bool
    contact_email: str | None
    staff_email: str | None
    logo_url: str | None
    branding_name: str | None

    model_config = {"from_attributes": True}


class PlatformDoctorCreateRequest(BaseModel):
    """Pre-provisions a team member — no password, by design: this is the
    "before generating credentials" step."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Literal[UserRole.PROVIDER, UserRole.ASSISTANT] = UserRole.PROVIDER
    license_number: str | None = None


class GenerateCredentialsResponse(BaseModel):
    temp_password: str
    emailed: bool
    email_error: str | None = None


class SendSetupLinkResponse(BaseModel):
    """setup_url is always returned (not just on email failure) so the
    admin can copy/paste and share it another way — text message, in
    person — exactly the same fallback GenerateCredentialsResponse gives
    for a temp password when email isn't configured or fails."""

    setup_url: str
    emailed: bool
    email_error: str | None = None


class ClinicDocumentResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    # Null = clinic-wide document; set = belongs to this one doctor (most
    # commonly a signed CONSENT_FORM granting the retention override).
    provider_id: uuid.UUID | None
    doc_type: ClinicDocumentType
    original_filename: str
    mime_type: str
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class RetentionUpdateRequest(BaseModel):
    """Toggles a doctor's data-retention override. Setting True is refused
    server-side unless a signed CONSENT_FORM document is already on file for
    that doctor (see PATCH /platform/users/{id}/retention) — turning it back
    False never requires one."""

    retain_all_sessions: bool


class PlatformAnalyticsResponse(BaseModel):
    clinics_count: int
    active_doctors_count: int
    sessions_this_week: int
    notes_signed_this_week: int
