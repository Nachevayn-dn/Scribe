import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.agent_common import ContactChannel
from app.models.outbound_message_log import OutboundMessageStatus, OutboundMessageType


class OutboundMessageLogResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID | None
    patient_id: uuid.UUID
    channel: ContactChannel
    message_type: OutboundMessageType
    body_text: str
    sent_at: datetime
    provider_message_id: str | None
    status: OutboundMessageStatus
    error_message: str | None

    model_config = {"from_attributes": True}
