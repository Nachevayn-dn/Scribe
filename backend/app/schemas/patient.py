import uuid
from datetime import date

from pydantic import BaseModel, Field


class PatientCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    date_of_birth: date
    mrn: str | None = None
    phone: str | None = None
    email: str | None = None


class PatientUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    mrn: str | None = None
    phone: str | None = None
    email: str | None = None


class PatientResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    mrn: str | None
    phone: str | None
    email: str | None

    model_config = {"from_attributes": True}
