import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole

ThemePreference = Literal["midnight", "jade"]


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    license_number: str | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    license_number: str | None = None


class UserSelfUpdateRequest(BaseModel):
    """Fields a user may change about their own account, regardless of
    role — distinct from UserUpdateRequest, which is SUPER_ADMIN-only."""

    theme_preference: ThemePreference | None = None
    notification_email: EmailStr | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    license_number: str | None
    photo_url: str | None
    theme_preference: str
    notification_email: str | None

    model_config = {"from_attributes": True}
