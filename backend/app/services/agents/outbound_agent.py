"""The outbound agent: sends the appointment confirmation once a doctor
approves a proposed slot (see api/calls.py's approve_appointment), and the
scheduled pre-procedure check-ins (day-before, hours-before) the reminder
scheduler triggers. One short forced-tool-call to Claude composes each
message — same shape as call_summary.py — using the clinic's outbound
knowledge-base documents as reference material (pre-op instructions, etc.),
then sends it on whichever channel the patient used during their inbound
call and logs it to OutboundMessageLog for audit + send-idempotency."""
import logging
import uuid

from anthropic import AsyncAnthropic
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.agent_common import AgentType, ContactChannel
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.appointment import Appointment
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.inbound_call_session import InboundCallSession
from app.models.outbound_agent_config import OutboundAgentConfig
from app.models.outbound_message_log import (
    OutboundMessageLog,
    OutboundMessageStatus,
    OutboundMessageType,
)
from app.models.patient import Patient
from app.models.user import User
from app.services.email_service import EmailNotConfiguredError, send_share_email
from app.services.telephony import twilio_client

settings = get_settings()
logger = logging.getLogger(__name__)


class OutboundAgentNotConfiguredError(RuntimeError):
    pass


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise OutboundAgentNotConfiguredError(
            "ANTHROPIC_API_KEY is not set — required for the outbound agent"
        )
    default_headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )
    return AsyncAnthropic(api_key=settings.anthropic_api_key, default_headers=default_headers)


_KIND_DESCRIPTIONS = {
    OutboundMessageType.APPOINTMENT_CONFIRMATION: (
        "Confirm the patient's appointment. Mention the date/time, the doctor, and what it's for."
    ),
    OutboundMessageType.REMINDER_DAY_BEFORE: (
        "Remind the patient their appointment is tomorrow. Include any relevant prep instructions "
        "from the reference material below (e.g. medication, fasting) if something applies."
    ),
    OutboundMessageType.REMINDER_HOURS_BEFORE: (
        "Remind the patient their appointment is coming up in a few hours. Check on anything "
        "time-sensitive from the reference material below (e.g. \"did you take your antibiotic\")."
    ),
}

_COMPOSE_TOOL = {
    "name": "record_message",
    "description": "Records the message text to send to the patient.",
    "input_schema": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
}


async def _compose_message(
    *,
    message_type: OutboundMessageType,
    patient: Patient,
    provider_name: str,
    appointment: Appointment,
    knowledge_documents: list[AgentKnowledgeDocument],
) -> str:
    system_prompt = (
        "You write short patient messages for a medical/dental clinic — sent by SMS, WhatsApp, "
        "or email. Plain text, no markdown, 2-4 sentences, warm but professional. Sign off with "
        "the clinic's name only if it reads naturally; don't invent details not given to you."
    )
    doc_sections = "\n\n".join(
        f"### {d.title}\n{(d.extracted_text or '')[:4000]}" for d in knowledge_documents if d.extracted_text
    )
    user_prompt = (
        f"{_KIND_DESCRIPTIONS[message_type]}\n\n"
        f"Patient: {patient.first_name} {patient.last_name}\n"
        f"Doctor: {provider_name}\n"
        f"Appointment: {appointment.scheduled_time.isoformat()}"
        + (f" — {appointment.reason}" if appointment.reason else "")
        + (f"\n\nReference material:\n{doc_sections}" if doc_sections else "")
    )

    client = _client()
    last_error: Exception | None = None
    for attempt in range(2):
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=system_prompt,
            tools=[_COMPOSE_TOOL],
            tool_choice={"type": "tool", "name": "record_message"},
            messages=[{"role": "user", "content": user_prompt}],
        )
        tool_use = next((b for b in message.content if b.type == "tool_use"), None)
        if tool_use is None:
            last_error = RuntimeError("Model did not call record_message")
            continue
        try:
            return tool_use.input["message"]
        except (KeyError, ValidationError) as exc:
            last_error = exc
            logger.warning("Outbound message composition failed on attempt %s: %s", attempt, exc)
            continue

    raise RuntimeError(f"Outbound message composition failed after retries: {last_error}")


async def _resolve_destination(
    db: AsyncSession, appointment: Appointment, patient: Patient
) -> tuple[ContactChannel, str] | None:
    """Prefers the channel/contact the patient actually used during the
    inbound call that led to this appointment, falling back to whatever
    contact info is on file for appointments booked another way."""
    call = (
        await db.execute(
            select(InboundCallSession).where(
                InboundCallSession.proposed_appointment_id == appointment.id
            )
        )
    ).scalar_one_or_none()

    if call and call.preferred_contact_channel:
        if call.preferred_contact_channel == ContactChannel.EMAIL and patient.email:
            return ContactChannel.EMAIL, patient.email
        if call.preferred_contact_channel in (ContactChannel.SMS, ContactChannel.WHATSAPP):
            return call.preferred_contact_channel, call.from_number

    if patient.email:
        return ContactChannel.EMAIL, patient.email
    if patient.phone:
        return ContactChannel.SMS, patient.phone
    return None


def _channel_enabled(config: OutboundAgentConfig, channel: ContactChannel) -> bool:
    return {
        ContactChannel.EMAIL: config.email_enabled,
        ContactChannel.SMS: config.sms_enabled,
        ContactChannel.WHATSAPP: config.whatsapp_enabled,
    }[channel]


async def _send_message(
    db: AsyncSession, appointment: Appointment, message_type: OutboundMessageType
) -> OutboundMessageLog:
    config = (
        await db.execute(
            select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == appointment.clinic_id)
        )
    ).scalar_one_or_none()
    if config is None or not config.enabled:
        raise OutboundAgentNotConfiguredError(
            "The outbound agent isn't enabled for this clinic yet — turn it on under "
            "Settings > Outbound agent."
        )

    patient = (
        await db.execute(select(Patient).where(Patient.id == appointment.patient_id))
    ).scalar_one_or_none()
    if patient is None:
        raise OutboundAgentNotConfiguredError("This appointment has no patient on file")

    destination = await _resolve_destination(db, appointment, patient)
    if destination is None:
        raise OutboundAgentNotConfiguredError("No contact channel is on file for this patient")
    channel, contact_value = destination

    if not _channel_enabled(config, channel):
        raise OutboundAgentNotConfiguredError(
            f"{channel.value.title()} sending isn't enabled for this clinic's outbound agent"
        )

    sms_from_number: str | None = None
    if channel == ContactChannel.SMS:
        sms_from_number = await _clinic_sms_from_number(db, appointment.clinic_id)
        if not sms_from_number:
            raise OutboundAgentNotConfiguredError(
                "No clinic phone number is provisioned yet — SMS can't be sent. "
                "Generate one under Settings > Telephony."
            )

    provider = (
        await db.execute(select(User).where(User.id == appointment.provider_id))
    ).scalar_one_or_none()
    provider_name = provider.full_name if provider else "your doctor"

    docs = (
        await db.execute(
            select(AgentKnowledgeDocument).where(
                AgentKnowledgeDocument.clinic_id == appointment.clinic_id,
                AgentKnowledgeDocument.agent_type == AgentType.OUTBOUND,
                AgentKnowledgeDocument.is_active.is_(True),
            )
        )
    ).scalars().all()

    body = await _compose_message(
        message_type=message_type,
        patient=patient,
        provider_name=provider_name,
        appointment=appointment,
        knowledge_documents=list(docs),
    )

    log = OutboundMessageLog(
        clinic_id=appointment.clinic_id,
        appointment_id=appointment.id,
        patient_id=patient.id,
        channel=channel,
        message_type=message_type,
        body_text=body,
    )
    try:
        if channel == ContactChannel.SMS:
            log.provider_message_id = twilio_client.send_sms(
                to=contact_value, body=body, from_number=sms_from_number
            )
        elif channel == ContactChannel.WHATSAPP:
            log.provider_message_id = twilio_client.send_whatsapp(to=contact_value, body=body)
        else:
            log.provider_message_id = send_share_email(
                to=[contact_value], subject="Your upcoming appointment", body_text=body
            )
        log.status = OutboundMessageStatus.SENT
    except (EmailNotConfiguredError, RuntimeError) as exc:
        logger.exception("Outbound %s send failed for appointment %s", message_type.value, appointment.id)
        log.status = OutboundMessageStatus.FAILED
        log.error_message = str(exc)

    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def _clinic_sms_from_number(db: AsyncSession, clinic_id: uuid.UUID) -> str | None:
    config = (
        await db.execute(select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id))
    ).scalar_one_or_none()
    return config.phone_number if config else None


async def send_appointment_confirmation(db: AsyncSession, appointment: Appointment) -> OutboundMessageLog:
    return await _send_message(db, appointment, OutboundMessageType.APPOINTMENT_CONFIRMATION)


async def send_reminder(
    db: AsyncSession, appointment: Appointment, kind: OutboundMessageType
) -> OutboundMessageLog:
    return await _send_message(db, appointment, kind)
