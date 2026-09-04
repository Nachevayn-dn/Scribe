import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class AppointmentCreateRequest(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    scheduled_time: datetime
    reason: str | None = None
    # The session this follow-up is being booked from, if any — e.g. the
    # "Schedule follow-up" button on a just-signed note.
    source_encounter_id: uuid.UUID | None = None


class AppointmentUpdateRequest(BaseModel):
    scheduled_time: datetime | None = None
    reason: str | None = None
    status: AppointmentStatus | None = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    created_by_id: uuid.UUID
    source_encounter_id: uuid.UUID | None
    scheduled_time: datetime
    reason: str | None
    status: AppointmentStatus
    created_at: datetime

    model_config = {"from_attributes": True}
