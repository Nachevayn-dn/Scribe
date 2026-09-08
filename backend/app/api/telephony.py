"""Public Twilio webhooks — voice call handling (turn-based via <Gather>)
and inbound WhatsApp messages. No auth dependency; Twilio calls these
directly, so every handler verifies the request signature first."""
import logging
import time as _clock
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from app.config import get_settings
from app.database import get_db
from app.models.agent_common import AgentType, ContactChannel
from app.models.agent_decision_rule import AgentDecisionRule
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic import Clinic
from app.models.inbound_agent_config import InboundAgentConfig, PickupMode, SummaryShareWith
from app.models.inbound_call_session import CallOutcome, InboundCallSession
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.services.agents import call_summary, inbound_agent
from app.services.agents.base import InboundAgentTurnResult
from app.services.email_service import EmailNotConfiguredError, send_share_email
from app.services.preference_engine import get_active_preferences
from app.services.telephony import elevenlabs_client, twilio_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telephony", tags=["telephony"])
settings = get_settings()

# Twilio's speech recognition/TTS need a full locale, not a bare ISO-639-1
# code. "ga"/"mt" (Irish/Maltese) aren't supported by Twilio — fall back to
# English rather than fail outright.
_TWILIO_LANGUAGE_MAP = {
    "en": "en-US", "bg": "bg-BG", "hr": "hr-HR", "cs": "cs-CZ", "da": "da-DK",
    "nl": "nl-NL", "et": "et-EE", "fi": "fi-FI", "fr": "fr-FR", "de": "de-DE",
    "el": "el-GR", "hu": "hu-HU", "it": "it-IT", "lv": "lv-LV", "lt": "lt-LT",
    "pl": "pl-PL", "pt": "pt-PT", "ro": "ro-RO", "sk": "sk-SK", "sl": "sl-SI",
    "es": "es-ES", "sv": "sv-SE", "ru": "ru-RU", "tr": "tr-TR",
}


def _twilio_lang(code: str) -> str:
    return _TWILIO_LANGUAGE_MAP.get(code, "en-US")


def _webhook_url(path: str) -> str:
    base = (settings.public_base_url or "").rstrip("/")
    return f"{base}{settings.api_v1_prefix}/telephony{path}"


# In-memory, single-use cache for ElevenLabs-generated audio clips (see
# _speak() below) — Twilio's <Play> needs a URL, not raw bytes, so each
# clip gets a short-lived token here and GET /tts-audio/{token} serves and
# immediately discards it. No task queue / no disk writes for the MVP,
# same "single in-process worker is enough at this scale" trade-off used
# throughout this app (see services/pipeline.py, reminder_scheduler.py);
# the opportunistic sweep below is just a safety net for a clip Twilio
# never actually fetched (e.g. the caller hung up mid-turn).
_TTS_CACHE: dict[str, bytes] = {}
_TTS_CACHE_TIMESTAMPS: dict[str, float] = {}
_TTS_CACHE_MAX_AGE_SECONDS = 300


def _evict_stale_tts_cache_entries() -> None:
    now = _clock.monotonic()
    stale = [token for token, ts in _TTS_CACHE_TIMESTAMPS.items() if now - ts > _TTS_CACHE_MAX_AGE_SECONDS]
    for token in stale:
        _TTS_CACHE.pop(token, None)
        _TTS_CACHE_TIMESTAMPS.pop(token, None)


async def _speak(vr: VoiceResponse, text: str, twilio_lang: str) -> None:
    """The one place both voice_incoming and voice_gather produce spoken
    output — uses ElevenLabs for a natural voice when configured, falling
    back to Twilio's own <Say> (unaffected either way) otherwise or if the
    ElevenLabs call fails, so a bad synthesis never breaks the call."""
    if settings.elevenlabs_api_key:
        try:
            audio_bytes = await elevenlabs_client.synthesize_speech(text)
            token = uuid.uuid4().hex
            _TTS_CACHE[token] = audio_bytes
            _TTS_CACHE_TIMESTAMPS[token] = _clock.monotonic()
            _evict_stale_tts_cache_entries()
            vr.play(_webhook_url(f"/tts-audio/{token}"))
            return
        except Exception:  # noqa: BLE001 — fall back rather than fail the call
            logger.exception("ElevenLabs synthesis failed, falling back to Twilio's voice")
    vr.say(text, language=twilio_lang)


def _within_after_hours(now_t: time, start: time | None, end: time | None) -> bool:
    if start is None or end is None:
        return False
    if start <= end:
        return start <= now_t <= end
    return now_t >= start or now_t <= end  # window wraps past midnight, e.g. 17:00 -> 09:00


def _parse_proposed_time(value: str | None) -> datetime:
    if value:
        try:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Could not parse proposed_time %r, defaulting to tomorrow", value)
    return datetime.now(timezone.utc) + timedelta(days=1)


def _parse_date_of_birth(value: str | None) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            logger.warning("Could not parse date_of_birth %r", value)
    # Unknown — the doctor can correct this once they see the proposed
    # appointment; better than failing the whole call.
    return date(1900, 1, 1)


async def _verify_signature(request: Request) -> dict:
    form = await request.form()
    params = {k: v for k, v in form.multi_items()}
    signature = request.headers.get("X-Twilio-Signature")
    if not twilio_client.verify_twilio_signature(str(request.url), params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return params


async def _pick_default_provider(db: AsyncSession, clinic_id: uuid.UUID) -> uuid.UUID | None:
    """Most clinics onboarded so far have one doctor; with several, the
    first active one is used. Not a real call-routing decision — a known
    simplification until the agent can ask which doctor the caller needs."""
    result = await db.execute(
        select(User.id)
        .where(
            User.clinic_id == clinic_id,
            User.role == UserRole.PROVIDER,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _load_agent_context(db: AsyncSession, clinic_id: uuid.UUID, provider_id: uuid.UUID | None):
    config = (
        await db.execute(select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id))
    ).scalar_one_or_none()

    docs = (
        await db.execute(
            select(AgentKnowledgeDocument).where(
                AgentKnowledgeDocument.clinic_id == clinic_id,
                AgentKnowledgeDocument.agent_type == AgentType.INBOUND,
                AgentKnowledgeDocument.is_active.is_(True),
            )
        )
    ).scalars().all()

    rules_stmt = select(AgentDecisionRule).where(
        AgentDecisionRule.clinic_id == clinic_id, AgentDecisionRule.is_active.is_(True)
    )
    rules_stmt = rules_stmt.where(
        (AgentDecisionRule.provider_id == provider_id) | (AgentDecisionRule.provider_id.is_(None))
        if provider_id
        else AgentDecisionRule.provider_id.is_(None)
    )
    rules = (await db.execute(rules_stmt.order_by(AgentDecisionRule.priority.asc()))).scalars().all()

    preferences = await get_active_preferences(db, provider_id) if provider_id else []
    return config, list(docs), list(rules), preferences


@router.get("/tts-audio/{token}")
async def get_tts_audio(token: str) -> Response:
    """Twilio's <Play> fetches the ElevenLabs-generated clip from here —
    see _speak() above. Single-use: served once, then discarded."""
    audio_bytes = _TTS_CACHE.pop(token, None)
    _TTS_CACHE_TIMESTAMPS.pop(token, None)
    if audio_bytes is None:
        raise HTTPException(status_code=404, detail="Audio not found or already played")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/voice/{clinic_id}/incoming")
async def voice_incoming(
    clinic_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    params = await _verify_signature(request)
    config = (
        await db.execute(select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id))
    ).scalar_one_or_none()

    vr = VoiceResponse()
    if config is None or not config.enabled:
        vr.say("Sorry, this line isn't taking calls right now.")
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    if config.pickup_mode == PickupMode.AFTER_HOURS:
        in_after_hours = _within_after_hours(datetime.now().time(), config.after_hours_start, config.after_hours_end)
        if not in_after_hours:
            if config.forward_to_number:
                vr.dial(config.forward_to_number)
            else:
                vr.say("Sorry, no one is available to take your call right now.")
                vr.hangup()
            return Response(content=str(vr), media_type="application/xml")
        # Within the after-hours window — fall through to the agent below.
    elif config.pickup_mode == PickupMode.NO_ANSWER and config.forward_to_number:
        # Rings the clinic's real line first; Twilio only continues past
        # <Dial> to the agent greeting below if it goes unanswered.
        vr.dial(config.forward_to_number, timeout=config.no_answer_timeout_seconds)

    call_sid = params.get("CallSid", "")
    from_number = params.get("From", "")
    provider_id = await _pick_default_provider(db, clinic_id)
    session = InboundCallSession(
        clinic_id=clinic_id, twilio_call_sid=call_sid, from_number=from_number, provider_id=provider_id,
        language_used=config.default_language,
    )
    db.add(session)
    await db.flush()
    await db.commit()

    if config.recording_enabled:
        start = vr.start()
        start.recording(
            recording_status_callback=_webhook_url(f"/voice/{clinic_id}/recording-status"),
            recording_status_callback_event="completed",
        )

    lang = _twilio_lang(config.default_language)
    await _speak(vr, config.greeting_text, lang)
    vr.gather(
        input="speech", action=_webhook_url(f"/voice/{clinic_id}/gather"), method="POST",
        speech_timeout="auto", language=lang,
    )
    return Response(content=str(vr), media_type="application/xml")


async def _find_or_create_patient(
    db: AsyncSession, clinic_id: uuid.UUID, from_number: str, result: InboundAgentTurnResult
) -> Patient:
    existing = (
        await db.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id, Patient.phone == from_number, Patient.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    first_name, _, last_name = (result.patient_full_name or "Unknown Caller").partition(" ")
    patient = Patient(
        clinic_id=clinic_id,
        first_name=first_name or "Unknown",
        last_name=last_name or "Caller",
        date_of_birth=_parse_date_of_birth(result.date_of_birth),
        phone=from_number,
        email=result.contact_value if result.contact_channel == "EMAIL" else None,
    )
    db.add(patient)
    await db.flush()
    return patient


async def _summary_recipients(db: AsyncSession, session: InboundCallSession, config: InboundAgentConfig) -> list[str]:
    emails: list[str] = []
    if session.provider_id:
        provider = (await db.execute(select(User).where(User.id == session.provider_id))).scalar_one_or_none()
        if provider:
            emails.append(provider.notification_email or provider.email)
    if config.share_summary_with == SummaryShareWith.TEAM:
        clinic = (await db.execute(select(Clinic).where(Clinic.id == session.clinic_id))).scalar_one_or_none()
        if clinic and clinic.staff_email:
            emails.append(clinic.staff_email)
    return [e for e in emails if e]


async def _share_summary(db: AsyncSession, session: InboundCallSession, config: InboundAgentConfig) -> None:
    try:
        session.summary_text = await call_summary.summarize_call(session.transcript_text)
    except Exception:  # noqa: BLE001 — never let summary failure block the call from finalizing
        logger.exception("Call summary generation failed for call %s", session.twilio_call_sid)
        await db.commit()
        return
    await db.commit()

    recipients = await _summary_recipients(db, session, config)
    if not recipients:
        return
    try:
        # SMS/WhatsApp sharing to the doctor needs a doctor phone number,
        # which doesn't exist in the data model yet — email is the one
        # channel that's fully wired up for summary delivery right now.
        send_share_email(to=recipients, subject="New inbound call summary", body_text=session.summary_text or "")
        session.summary_shared_at = datetime.now(timezone.utc)
        await db.commit()
    except (EmailNotConfiguredError, RuntimeError):
        logger.exception("Failed to share call summary for call %s", session.twilio_call_sid)


async def _finalize_call(
    db: AsyncSession, session: InboundCallSession, config: InboundAgentConfig, result: InboundAgentTurnResult
) -> None:
    session.ended_at = datetime.now(timezone.utc)
    if session.started_at:
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

    if result.action == "propose_appointment":
        session.outcome = CallOutcome.APPOINTMENT_PROPOSED
        if result.contact_channel:
            session.preferred_contact_channel = ContactChannel(result.contact_channel)
        patient = await _find_or_create_patient(db, session.clinic_id, session.from_number, result)
        session.patient_id = patient.id
        if session.provider_id:
            appointment = Appointment(
                clinic_id=session.clinic_id,
                patient_id=patient.id,
                provider_id=session.provider_id,
                created_by_id=session.provider_id,
                scheduled_time=_parse_proposed_time(result.proposed_time),
                reason=result.reason,
                status=AppointmentStatus.PROPOSED,
            )
            db.add(appointment)
            await db.flush()
            session.proposed_appointment_id = appointment.id
    elif result.action == "escalate_emergency":
        session.outcome = CallOutcome.EMERGENCY_ESCALATED
    else:
        session.outcome = CallOutcome.INFO_ONLY

    await db.commit()
    await _share_summary(db, session, config)


@router.post("/voice/{clinic_id}/gather")
async def voice_gather(
    clinic_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    params = await _verify_signature(request)
    call_sid = params.get("CallSid", "")
    speech_result = params.get("SpeechResult") or None

    session = (
        await db.execute(
            select(InboundCallSession).where(
                InboundCallSession.twilio_call_sid == call_sid, InboundCallSession.clinic_id == clinic_id
            )
        )
    ).scalar_one_or_none()

    vr = VoiceResponse()
    if session is None:
        vr.say("Sorry, something went wrong. Please call back.")
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    config, docs, rules, preferences = await _load_agent_context(db, clinic_id, session.provider_id)
    if speech_result:
        session.transcript_text += f"Caller: {speech_result}\n"

    try:
        result = await inbound_agent.next_turn(
            config=config,
            knowledge_documents=docs,
            decision_rules=rules,
            preferences=preferences,
            transcript_so_far=session.transcript_text,
            latest_caller_utterance=speech_result,
        )
    except Exception:  # noqa: BLE001 — a bad call is better than a crashed webhook
        logger.exception("Inbound agent turn failed for call %s", call_sid)
        vr.say("Sorry, I'm having trouble right now. Please try calling back shortly.")
        vr.hangup()
        session.ended_at = datetime.now(timezone.utc)
        session.outcome = CallOutcome.ABANDONED
        await db.commit()
        await _share_summary(db, session, config)
        return Response(content=str(vr), media_type="application/xml")

    session.transcript_text += f"Agent: {result.say_text}\n"
    if result.detected_language and result.detected_language != session.language_used:
        session.language_used = result.detected_language
    lang = _twilio_lang(session.language_used or config.default_language)

    if result.action == "continue":
        await _speak(vr, result.say_text, lang)
        vr.gather(
            input="speech", action=_webhook_url(f"/voice/{clinic_id}/gather"), method="POST",
            speech_timeout="auto", language=lang,
        )
        await db.commit()
        return Response(content=str(vr), media_type="application/xml")

    await _speak(vr, result.say_text, lang)
    vr.hangup()
    await _finalize_call(db, session, config, result)
    return Response(content=str(vr), media_type="application/xml")


@router.post("/voice/{clinic_id}/status")
async def voice_status(
    clinic_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    """Safety net for calls that end without going through a terminal tool
    call (the caller just hangs up mid-conversation)."""
    params = await _verify_signature(request)
    call_sid = params.get("CallSid", "")
    call_status = params.get("CallStatus")

    session = (
        await db.execute(
            select(InboundCallSession).where(
                InboundCallSession.twilio_call_sid == call_sid, InboundCallSession.clinic_id == clinic_id
            )
        )
    ).scalar_one_or_none()

    if session and session.ended_at is None and call_status in ("completed", "busy", "failed", "no-answer", "canceled"):
        config = (
            await db.execute(select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one_or_none()
        session.ended_at = datetime.now(timezone.utc)
        session.outcome = CallOutcome.ABANDONED
        if session.started_at:
            session.duration_seconds = int(
                (session.ended_at - session.started_at).total_seconds()
            )
        await db.commit()
        if config:
            await _share_summary(db, session, config)
    return Response(status_code=204)


@router.post("/voice/{clinic_id}/recording-status")
async def voice_recording_status(
    clinic_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    params = await _verify_signature(request)
    session = (
        await db.execute(
            select(InboundCallSession).where(
                InboundCallSession.twilio_call_sid == params.get("CallSid", ""),
                InboundCallSession.clinic_id == clinic_id,
            )
        )
    ).scalar_one_or_none()
    if session:
        session.recording_sid = params.get("RecordingSid")
        session.recording_url = params.get("RecordingUrl")
        await db.commit()
    return Response(status_code=204)


@router.post("/whatsapp/{clinic_id}/incoming")
async def whatsapp_incoming(
    clinic_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    params = await _verify_signature(request)
    from_number = params.get("From", "")
    body = params.get("Body", "")

    session = (
        await db.execute(
            select(InboundCallSession)
            .where(
                InboundCallSession.clinic_id == clinic_id,
                InboundCallSession.from_number == from_number,
                InboundCallSession.ended_at.is_(None),
            )
            .order_by(InboundCallSession.started_at.desc())
        )
    ).scalars().first()

    if session is None:
        provider_id = await _pick_default_provider(db, clinic_id)
        session = InboundCallSession(
            clinic_id=clinic_id,
            twilio_call_sid=f"whatsapp:{params.get('MessageSid', uuid.uuid4().hex)}",
            from_number=from_number,
            provider_id=provider_id,
        )
        db.add(session)
        await db.flush()

    config, docs, rules, preferences = await _load_agent_context(db, clinic_id, session.provider_id)
    if config is None or not config.enabled:
        return Response(status_code=204)
    if session.language_used is None:
        session.language_used = config.default_language

    session.transcript_text += f"Caller: {body}\n"
    try:
        result = await inbound_agent.next_turn(
            config=config,
            knowledge_documents=docs,
            decision_rules=rules,
            preferences=preferences,
            transcript_so_far=session.transcript_text,
            latest_caller_utterance=body,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Inbound agent WhatsApp turn failed for %s", from_number)
        await db.commit()
        return Response(status_code=204)

    session.transcript_text += f"Agent: {result.say_text}\n"
    if result.detected_language and result.detected_language != session.language_used:
        session.language_used = result.detected_language
    mr = MessagingResponse()
    mr.message(result.say_text)

    if result.action == "continue":
        await db.commit()
    else:
        await _finalize_call(db, session, config, result)

    return Response(content=str(mr), media_type="application/xml")
