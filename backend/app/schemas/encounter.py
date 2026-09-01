import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.encounter import EncounterStatus


class EncounterCreateRequest(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID


class EncounterResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    created_by_id: uuid.UUID
    status: EncounterStatus
    failure_reason: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class AudioFileResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    mime_type: str
    duration_seconds: float | None
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
