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

    model_config = {"from_attributes": True}


class ClinicUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
    contact_email: EmailStr | None = None
    staff_email: EmailStr | None = None
