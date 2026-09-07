"""Shared result types for the inbound call agent — kept in one place the
same way services/extraction/base.py centralizes its provider's result
shapes, so api/telephony.py and tests both import from a single spot."""
from typing import Literal

from pydantic import BaseModel


class InboundAgentTurnResult(BaseModel):
    """What the agent decided to do on one conversational turn. `say_text`
    is always present — even a terminal action needs a closing line before
    the call ends."""

    action: Literal["continue", "propose_appointment", "escalate_emergency", "end_call"]
    say_text: str

    # Set whenever the agent detects the caller is speaking a different
    # (clinic-supported) language than the current turn was in — lets
    # api/telephony.py switch Twilio's speech-recognition/voice locale to
    # match on the very next turn, without the caller having to ask.
    detected_language: str | None = None

    # Only populated when action == "propose_appointment".
    patient_full_name: str | None = None
    date_of_birth: str | None = None  # ISO 8601 (YYYY-MM-DD)
    reason: str | None = None
    proposed_time: str | None = None  # ISO 8601, clinic-local
    contact_channel: Literal["EMAIL", "SMS", "WHATSAPP"] | None = None
    contact_value: str | None = None
