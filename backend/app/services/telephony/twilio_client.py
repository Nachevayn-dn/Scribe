"""Twilio integration — phone number provisioning, SMS/WhatsApp sending,
and webhook signature verification for the inbound/outbound agents.

Buying a number and sending messages/call minutes are real, billed usage on
the clinic operator's own Twilio account — unlike Resend's free tier,
nothing here is free. Mirrors email_service.py's shape: a clean "not
configured" error instead of a crash when no credentials are set, and
provider exceptions wrapped into clean RuntimeErrors rather than raw
tracebacks reaching the API layer.
"""
import logging
import uuid

from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class TwilioNotConfiguredError(RuntimeError):
    pass


def _client() -> Client:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise TwilioNotConfiguredError(
            "Twilio isn't set up yet — add your Account SID and Auth Token under "
            "Settings > Telephony."
        )
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _voice_webhook_url(clinic_id: uuid.UUID) -> str:
    if not settings.public_base_url:
        raise TwilioNotConfiguredError(
            "No public URL is set yet (PUBLIC_BASE_URL) — the number can still be "
            "bought, but calls won't route anywhere until this is configured."
        )
    base = settings.public_base_url.rstrip("/")
    return f"{base}{settings.api_v1_prefix}/telephony/voice/{clinic_id}/incoming"


def provision_phone_number(clinic_id: uuid.UUID, country: str = "US") -> tuple[str, str]:
    """Buys a real phone number on the operator's Twilio account and, if
    PUBLIC_BASE_URL is set, points its voice webhook at this backend.
    Returns (phone_number, phone_number_sid)."""
    client = _client()
    try:
        available = client.available_phone_numbers(country).local.list(
            voice_enabled=True, sms_enabled=True, limit=1
        )
        if not available:
            raise RuntimeError(f"No available phone numbers found for country {country!r}")

        voice_url = None
        if settings.public_base_url:
            voice_url = _voice_webhook_url(clinic_id)

        purchased = client.incoming_phone_numbers.create(
            phone_number=available[0].phone_number,
            voice_url=voice_url,
            voice_method="POST",
        )
    except TwilioRestException as exc:
        logger.exception("Twilio number provisioning failed")
        raise RuntimeError(f"Failed to provision a phone number: {exc}") from exc
    return purchased.phone_number, purchased.sid


def configure_number_webhooks(phone_number_sid: str, clinic_id: uuid.UUID) -> None:
    """(Re)points an already-purchased number's webhooks at the current
    PUBLIC_BASE_URL — call this after that setting changes (e.g. a fresh
    ngrok URL each session)."""
    client = _client()
    voice_url = _voice_webhook_url(clinic_id)
    try:
        client.incoming_phone_numbers(phone_number_sid).update(
            voice_url=voice_url,
            voice_method="POST",
            status_callback=voice_url.replace("/incoming", "/status"),
            status_callback_method="POST",
        )
    except TwilioRestException as exc:
        raise RuntimeError(f"Failed to update Twilio webhook configuration: {exc}") from exc


def send_sms(to: str, body: str, from_number: str) -> str:
    """Returns the Twilio message SID."""
    client = _client()
    try:
        message = client.messages.create(to=to, from_=from_number, body=body)
    except TwilioRestException as exc:
        logger.exception("Twilio SMS send failed")
        raise RuntimeError(f"Failed to send SMS: {exc}") from exc
    return message.sid


def send_whatsapp(to: str, body: str, from_number: str | None = None) -> str:
    """from_number defaults to the shared Twilio sandbox sender
    (TWILIO_WHATSAPP_FROM) unless the clinic has its own approved WhatsApp
    Business number configured. Returns the Twilio message SID."""
    client = _client()
    sender = from_number or settings.twilio_whatsapp_from
    to_whatsapp = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    try:
        message = client.messages.create(to=to_whatsapp, from_=sender, body=body)
    except TwilioRestException as exc:
        logger.exception("Twilio WhatsApp send failed")
        raise RuntimeError(f"Failed to send WhatsApp message: {exc}") from exc
    return message.sid


def verify_twilio_signature(request_url: str, params: dict, signature: str | None) -> bool:
    """Confirms an incoming webhook POST really came from Twilio, using the
    same auth token as everything else here. Every public telephony webhook
    (api/telephony.py) must call this before acting on the request body."""
    if not settings.twilio_auth_token or not signature:
        return False
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(request_url, params, signature)
