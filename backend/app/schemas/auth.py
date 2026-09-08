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


class SetupTokenInfoResponse(BaseModel):
    """Shown before the password form itself, so the page can say "Setting
    a password for Dana Nacheva (dana@...)" rather than asking blind."""

    email: str
    full_name: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    clinic_name: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    photo_url: str | None
    theme_preference: str
    notification_email: str | None
    language_preference: str | None
    is_platform_admin: bool

    model_config = {"from_attributes": True}
