import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.agent_common import ContactChannel
from app.models.inbound_call_session import CallOutcome


class CallSessionResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID | None
    provider_id: uuid.UUID | None
    from_number: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    # Twilio hosts the recording itself — this is a reference, not a copy.
    # The frontend plays it back through an authenticated proxy, never this
    # raw Twilio URL directly.
    recording_sid: str | None
    recording_url: str | None
    transcript_text: str
    summary_text: str | None
    outcome: CallOutcome
    proposed_appointment_id: uuid.UUID | None
    preferred_contact_channel: ContactChannel | None
    language_used: str | None
    summary_shared_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
