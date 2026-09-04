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


class PlatformClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_active: bool
    contact_email: str | None
    staff_email: str | None

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


class ClinicDocumentResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    doc_type: ClinicDocumentType
    original_filename: str
    mime_type: str
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformAnalyticsResponse(BaseModel):
    clinics_count: int
    active_doctors_count: int
    sessions_this_week: int
    notes_signed_this_week: int
