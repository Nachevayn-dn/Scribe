import uuid

from pydantic import BaseModel, Field


class ClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ClinicUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
