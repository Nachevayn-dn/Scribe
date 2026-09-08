"""Inbound voice/WhatsApp webhooks (api/telephony.py). Twilio's signature
check and the Claude-powered agent turn are both mocked — no live external
calls — same pattern as test_telephony.py's provider mocking, applied to
the conversational flow instead of the config CRUD."""
import uuid
from datetime import time
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from app.models.appointment import Appointment, AppointmentStatus
from app.models.inbound_agent_config import InboundAgentConfig, PickupMode
from app.models.inbound_call_session import CallOutcome, InboundCallSession
from app.models.patient import Patient
from app.models.user import User
from app.services.agents.base import InboundAgentTurnResult
from tests.conftest import TestSessionLocal, create_user, signup_clinic

VOICE_URL = "/api/v1/telephony/voice/{clinic_id}/incoming"
GATHER_URL = "/api/v1/telephony/voice/{clinic_id}/gather"
STATUS_URL = "/api/v1/telephony/voice/{clinic_id}/status"
RECORDING_URL = "/api/v1/telephony/voice/{clinic_id}/recording-status"
WHATSAPP_URL = "/api/v1/telephony/whatsapp/{clinic_id}/incoming"


async def _setup_clinic_with_provider(client: AsyncClient) -> dict:
    """A signed-up clinic (SUPER_ADMIN) plus one PROVIDER user, so
    _pick_default_provider has someone to find."""
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == admin["email"]))
        clinic_id = result.scalar_one().clinic_id
    return {"admin": admin, "provider": provider, "clinic_id": clinic_id}


async def _enable_config(clinic_id: uuid.UUID, **overrides) -> None:
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundAgentConfig).where(InboundAgentConfig.clinic_id == clinic_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            config = InboundAgentConfig(clinic_id=clinic_id)
            session.add(config)
        config.enabled = True
        for key, value in overrides.items():
            setattr(config, key, value)
        await session.commit()


def _patch_signature_ok():
    return patch("app.api.telephony.twilio_client.verify_twilio_signature", return_value=True)


async def test_incoming_call_bad_signature_is_rejected(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    with patch("app.api.telephony.twilio_client.verify_twilio_signature", return_value=False):
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA123", "From": "+15550001111"},
        )
    assert resp.status_code == 403


async def test_incoming_call_when_agent_disabled_says_sorry_and_hangs_up(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    # No InboundAgentConfig row exists yet for this clinic — config is None.
    with _patch_signature_ok():
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-disabled", "From": "+15550001111"},
        )
    assert resp.status_code == 200
    assert "<Hangup" in resp.text
    assert "Sorry" in resp.text


async def test_incoming_call_after_hours_forwards_when_outside_window(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(
        setup["clinic_id"],
        pickup_mode=PickupMode.AFTER_HOURS,
        after_hours_start=time(17, 0),
        after_hours_end=time(9, 0),
        forward_to_number="+15559998888",
    )
    # Pin "now" to 12:00 (a time provably outside the 17:00->09:00 window)
    # rather than depending on the real wall clock, which would make this
    # test flaky depending on when it happens to run.
    with _patch_signature_ok(), patch("app.api.telephony.datetime") as mock_datetime:
        mock_datetime.now.return_value.time.return_value = time(12, 0)
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-forward", "From": "+15550001111"},
        )
    assert resp.status_code == 200
    assert "<Dial>+15559998888</Dial>" in resp.text


async def test_incoming_call_after_hours_falls_through_inside_window(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(
        setup["clinic_id"],
        pickup_mode=PickupMode.AFTER_HOURS,
        after_hours_start=time(17, 0),
        after_hours_end=time(9, 0),
        forward_to_number="+15559998888",
    )
    with _patch_signature_ok(), patch("app.api.telephony.datetime") as mock_datetime:
        mock_datetime.now.return_value.time.return_value = time(22, 0)  # inside 17:00->09:00
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-after-hours-live", "From": "+15550001111"},
        )
    assert resp.status_code == 200
    assert "<Gather" in resp.text
    assert "<Dial>" not in resp.text


async def test_incoming_call_no_answer_mode_dials_before_agent(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(
        setup["clinic_id"],
        pickup_mode=PickupMode.NO_ANSWER,
        forward_to_number="+15559997777",
        no_answer_timeout_seconds=8,
    )
    with _patch_signature_ok():
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-no-answer", "From": "+15550001111"},
        )
    assert resp.status_code == 200
    assert '<Dial timeout="8">+15559997777</Dial>' in resp.text
    assert "<Gather" in resp.text  # falls through to the agent if unanswered


def test_within_after_hours_handles_wrapping_and_non_wrapping_windows():
    from app.api.telephony import _within_after_hours

    # Non-wrapping window (start <= end): 09:00 -> 17:00.
    assert _within_after_hours(time(12, 0), time(9, 0), time(17, 0)) is True
    assert _within_after_hours(time(8, 0), time(9, 0), time(17, 0)) is False
    assert _within_after_hours(time(18, 0), time(9, 0), time(17, 0)) is False

    # Wrapping window (start > end): 17:00 -> 09:00, crossing midnight.
    assert _within_after_hours(time(22, 0), time(17, 0), time(9, 0)) is True
    assert _within_after_hours(time(3, 0), time(17, 0), time(9, 0)) is True
    assert _within_after_hours(time(12, 0), time(17, 0), time(9, 0)) is False

    # No configured window at all.
    assert _within_after_hours(time(12, 0), None, None) is False


def test_twilio_lang_maps_russian_and_turkish():
    from app.api.telephony import _twilio_lang

    assert _twilio_lang("ru") == "ru-RU"
    assert _twilio_lang("tr") == "tr-TR"
    assert _twilio_lang("xx") == "en-US"  # unknown code falls back safely


async def test_incoming_call_creates_session_and_gathers(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        resp = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-new-call", "From": "+15550001111"},
        )
    assert resp.status_code == 200
    assert "<Gather" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-new-call")
        )
        call = result.scalar_one()
        assert call.from_number == "+15550001111"
        assert str(call.provider_id) == setup["provider"]["id"]
        assert call.outcome == CallOutcome.IN_PROGRESS


async def test_gather_continue_keeps_listening(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-continue", "From": "+15550001111"},
        )

    turn_result = InboundAgentTurnResult(action="continue", say_text="What's your date of birth?")
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ):
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-continue", "SpeechResult": "I need an appointment"},
        )
    assert resp.status_code == 200
    assert "<Gather" in resp.text
    assert "What's your date of birth?" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-continue")
        )
        call = result.scalar_one()
        assert "I need an appointment" in call.transcript_text
        assert call.outcome == CallOutcome.IN_PROGRESS


async def test_gather_switches_locale_when_caller_speaks_another_language(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"], additional_languages=["es"])  # default stays "en"

    with _patch_signature_ok():
        incoming = await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-lang-switch", "From": "+15550001111"},
        )
    assert 'language="en-US"' in incoming.text  # greeting still in the clinic default

    turn_result = InboundAgentTurnResult(
        action="continue", say_text="¿En qué puedo ayudarle?", detected_language="es"
    )
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ):
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-lang-switch", "SpeechResult": "Hola, necesito una cita"},
        )
    assert resp.status_code == 200
    assert 'language="es-ES"' in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-lang-switch")
        )
        call = result.scalar_one()
        assert call.language_used == "es"

    # A follow-up turn back in English should switch the locale back too.
    turn_result_en = InboundAgentTurnResult(
        action="continue", say_text="Sure, what's the date of birth?", detected_language="en"
    )
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result_en)
    ):
        resp2 = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-lang-switch", "SpeechResult": "Actually let's continue in English"},
        )
    assert 'language="en-US"' in resp2.text


async def test_gather_propose_appointment_creates_patient_and_appointment(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-propose", "From": "+15550002222"},
        )

    turn_result = InboundAgentTurnResult(
        action="propose_appointment",
        say_text="You're all set, we'll confirm shortly.",
        patient_full_name="Jane Doe",
        date_of_birth="1985-04-12",
        reason="dental implant consultation",
        proposed_time="2026-09-10T10:00:00+00:00",
        contact_channel="SMS",
        contact_value="+15550002222",
    )
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="Jane called about implants.")
    ), patch(
        "app.api.telephony.send_share_email", return_value="msg-id"
    ) as mock_email:
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-propose", "SpeechResult": "yes that works"},
        )
    assert resp.status_code == 200
    assert "<Hangup" in resp.text
    assert "confirm shortly" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-propose")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.APPOINTMENT_PROPOSED
        assert call.ended_at is not None
        assert call.summary_text == "Jane called about implants."
        assert call.summary_shared_at is not None

        patient_result = await session.execute(
            select(Patient).where(Patient.id == call.patient_id)
        )
        patient = patient_result.scalar_one()
        assert patient.first_name == "Jane"
        assert patient.last_name == "Doe"

        appt_result = await session.execute(
            select(Appointment).where(Appointment.id == call.proposed_appointment_id)
        )
        appointment = appt_result.scalar_one()
        assert appointment.status == AppointmentStatus.PROPOSED
        assert appointment.patient_id == patient.id
        assert str(appointment.provider_id) == setup["provider"]["id"]

    mock_email.assert_called_once()


async def test_gather_escalate_emergency(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-emergency", "From": "+15550003333"},
        )

    turn_result = InboundAgentTurnResult(
        action="escalate_emergency", say_text="Please hang up and call 911 immediately."
    )
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="Possible emergency.")
    ), patch("app.api.telephony.send_share_email", return_value="msg-id"):
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-emergency", "SpeechResult": "I can't breathe"},
        )
    assert resp.status_code == 200
    assert "911" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-emergency")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.EMERGENCY_ESCALATED


async def test_gather_agent_error_marks_call_abandoned(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-error", "From": "+15550004444"},
        )

    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(side_effect=RuntimeError("boom"))
    ), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="n/a")
    ):
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-error", "SpeechResult": "hello?"},
        )
    assert resp.status_code == 200
    assert "trouble" in resp.text.lower()

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-error")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.ABANDONED
        assert call.ended_at is not None


async def test_gather_unknown_call_sid_is_handled_gracefully(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        resp = await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-never-existed", "SpeechResult": "hello"},
        )
    assert resp.status_code == 200
    assert "<Hangup" in resp.text


async def test_status_callback_marks_abandoned_when_call_ends_unfinished(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-status", "From": "+15550005555"},
        )

    with _patch_signature_ok(), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="Caller hung up.")
    ), patch("app.api.telephony.send_share_email", return_value="msg-id"):
        resp = await client.post(
            STATUS_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-status", "CallStatus": "no-answer"},
        )
    assert resp.status_code == 204

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-status")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.ABANDONED
        assert call.ended_at is not None


async def test_status_callback_is_a_noop_once_call_already_finalized(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-already-done", "From": "+15550006666"},
        )
    turn_result = InboundAgentTurnResult(action="end_call", say_text="Goodbye.")
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="All good.")
    ), patch("app.api.telephony.send_share_email", return_value="msg-id"):
        await client.post(
            GATHER_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-already-done", "SpeechResult": "nothing else"},
        )

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-already-done")
        )
        ended_at_before = result.scalar_one().ended_at

    with _patch_signature_ok():
        resp = await client.post(
            STATUS_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-already-done", "CallStatus": "completed"},
        )
    assert resp.status_code == 204

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-already-done")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.INFO_ONLY  # untouched by the status callback
        assert call.ended_at == ended_at_before


async def test_recording_status_saves_recording_reference(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    with _patch_signature_ok():
        await client.post(
            VOICE_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-recording", "From": "+15550007777"},
        )
        resp = await client.post(
            RECORDING_URL.format(clinic_id=setup["clinic_id"]),
            data={"CallSid": "CA-recording", "RecordingSid": "RE123", "RecordingUrl": "https://api.twilio.com/rec"},
        )
    assert resp.status_code == 204

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.twilio_call_sid == "CA-recording")
        )
        call = result.scalar_one()
        assert call.recording_sid == "RE123"
        assert call.recording_url == "https://api.twilio.com/rec"


async def test_whatsapp_incoming_creates_session_and_replies(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    turn_result = InboundAgentTurnResult(action="continue", say_text="Sure, what's your name?")
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ):
        resp = await client.post(
            WHATSAPP_URL.format(clinic_id=setup["clinic_id"]),
            data={"From": "whatsapp:+15550008888", "Body": "Hi, I'd like to book a cleaning", "MessageSid": "SM1"},
        )
    assert resp.status_code == 200
    assert "Sure, what's your name?" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.from_number == "whatsapp:+15550008888")
        )
        call = result.scalar_one()
        assert call.ended_at is None
        assert "book a cleaning" in call.transcript_text


async def test_whatsapp_incoming_finalizes_on_terminal_action(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    await _enable_config(setup["clinic_id"])

    turn_result = InboundAgentTurnResult(action="end_call", say_text="Glad I could help!")
    with _patch_signature_ok(), patch(
        "app.api.telephony.inbound_agent.next_turn", new=AsyncMock(return_value=turn_result)
    ), patch(
        "app.api.telephony.call_summary.summarize_call", new=AsyncMock(return_value="Answered a question.")
    ), patch("app.api.telephony.send_share_email", return_value="msg-id"):
        resp = await client.post(
            WHATSAPP_URL.format(clinic_id=setup["clinic_id"]),
            data={"From": "whatsapp:+15550009999", "Body": "What are your hours?", "MessageSid": "SM2"},
        )
    assert resp.status_code == 200
    assert "Glad I could help" in resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(InboundCallSession).where(InboundCallSession.from_number == "whatsapp:+15550009999")
        )
        call = result.scalar_one()
        assert call.outcome == CallOutcome.INFO_ONLY
        assert call.ended_at is not None


async def test_whatsapp_incoming_disabled_agent_is_silent(client: AsyncClient):
    setup = await _setup_clinic_with_provider(client)
    # Config not enabled — endpoint should be a no-op, not error.
    with _patch_signature_ok():
        resp = await client.post(
            WHATSAPP_URL.format(clinic_id=setup["clinic_id"]),
            data={"From": "whatsapp:+15550001010", "Body": "Hello?", "MessageSid": "SM3"},
        )
    assert resp.status_code == 204
