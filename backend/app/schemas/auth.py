import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class SignupClinicRequest(BaseModel):
    clinic_name: str = Field(min_length=1, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=255)
    admin_full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    photo_url: str | None
    theme_preference: str
    notification_email: str | None

    model_config = {"from_attributes": True}
