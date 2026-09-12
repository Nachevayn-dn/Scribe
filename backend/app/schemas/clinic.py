import uuid

from pydantic import BaseModel, EmailStr, Field


class ClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_active: bool
    contact_email: str | None
    staff_email: str | None
    # White-label override — null for every clinic unless a platform admin
    # has set one (see PLATFORM_ADMIN-gated /platform/clinics/{id}/logo).
    logo_url: str | None
    branding_name: str | None

    model_config = {"from_attributes": True}


class ClinicUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
    contact_email: EmailStr | None = None
    staff_email: EmailStr | None = None


class ClinicGreetingResponse(BaseModel):
    greeting_text: str


class ClinicGreetingUpdateRequest(BaseModel):
    greeting_text: str = Field(min_length=1, max_length=1000)
