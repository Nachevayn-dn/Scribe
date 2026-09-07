import uuid
from datetime import time

from pydantic import BaseModel, Field

from app.models.agent_common import ContactChannel
from app.models.inbound_agent_config import PickupMode, SummaryShareWith


class InboundAgentConfigResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    enabled: bool
    phone_number: str | None
    phone_number_sid: str | None
    whatsapp_number: str | None
    default_language: str
    additional_languages: list[str]
    greeting_text: str
    pickup_mode: PickupMode
    after_hours_start: time | None
    after_hours_end: time | None
    no_answer_timeout_seconds: int
    forward_to_number: str | None
    recording_enabled: bool
    share_summary_with: SummaryShareWith
    share_channel: ContactChannel

    model_config = {"from_attributes": True}


class InboundAgentConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    default_language: str | None = None
    additional_languages: list[str] | None = None
    greeting_text: str | None = Field(default=None, min_length=1, max_length=1000)
    pickup_mode: PickupMode | None = None
    after_hours_start: time | None = None
    after_hours_end: time | None = None
    no_answer_timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    forward_to_number: str | None = None
    recording_enabled: bool | None = None
    share_summary_with: SummaryShareWith | None = None
    share_channel: ContactChannel | None = None


class ProvisionNumberResponse(BaseModel):
    phone_number: str
    phone_number_sid: str
    webhook_configured: bool


class ConnectWhatsAppRequest(BaseModel):
    # Omit to use Twilio's shared sandbox sender; pass your own
    # Meta-verified WhatsApp Business number once approved.
    whatsapp_number: str | None = None


class OutboundAgentConfigResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    enabled: bool
    day_before_enabled: bool
    day_before_send_hour: time
    hours_before_enabled: bool
    hours_before_offset: int
    default_language: str
    additional_languages: list[str]
    email_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool

    model_config = {"from_attributes": True}


class OutboundAgentConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    day_before_enabled: bool | None = None
    day_before_send_hour: time | None = None
    hours_before_enabled: bool | None = None
    hours_before_offset: int | None = Field(default=None, ge=1, le=48)
    default_language: str | None = None
    additional_languages: list[str] | None = None
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
