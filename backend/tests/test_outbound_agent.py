"""services/agents/outbound_agent.py: destination resolution, channel
gating, and OutboundMessageLog bookkeeping. Message composition (the
Claude call) is mocked — no live external calls — same convention as the
inbound agent's tests mocking next_turn/summarize_call directly."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.agent_common import ContactChannel
from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic import Clinic
from app.models.inbound_agent_config import InboundAgentConfig
from app.models.inbound_call_session import CallOutcome, InboundCallSession
from app.models.outbound_agent_config import OutboundAgentConfig
from app.models.outbound_message_log import OutboundMessageLog, OutboundMessageStatus, OutboundMessageType
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.services.agents import outbound_agent
from app.services.agents.outbound_agent import OutboundAgentNotConfiguredError
from tests.conftest import TestSessionLocal


async def _make_clinic() -> uuid.UUID:
    async with TestSessionLocal() as session:
        clinic = Clinic(name=f"Outbound Test Clinic {uuid.uuid4().hex[:8]}")
        session.add(clinic)
        await session.commit()
        await session.refresh(clinic)
        return clinic.id


async def _make_provider(clinic_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        user = User(
            clinic_id=clinic_id,
            email=f"doc-{uuid.uuid4().hex[:8]}@example.com",
            full_name="Dr. Outbound Test",
            role=UserRole.PROVIDER,
            hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _make_patient(clinic_id: uuid.UUID, *, email: str | None = None, phone: str | None = None) -> uuid.UUID:
    async with TestSessionLocal() as session:
        patient = Patient(
            clinic_id=clinic_id, first_name="Jane", last_name="Doe",
            date_of_birth=datetime(1985, 4, 12).date(), email=email, phone=phone,
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient.id


async def _make_appointment(clinic_id: uuid.UUID, patient_id: uuid.UUID, provider_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        appointment = Appointment(
            clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id, created_by_id=provider_id,
            scheduled_time=datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc), reason="Implant consultation",
            status=AppointmentStatus.SCHEDULED,
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        return appointment.id


async def _make_outbound_config(clinic_id: uuid.UUID, **overrides) -> None:
    async with TestSessionLocal() as session:
        config = OutboundAgentConfig(clinic_id=clinic_id, enabled=True, **overrides)
        session.add(config)
        await session.commit()


async def _make_call(
    clinic_id: uuid.UUID, appointment_id: uuid.UUID, *, channel: ContactChannel, from_number: str
) -> None:
    async with TestSessionLocal() as session:
        call = InboundCallSession(
            clinic_id=clinic_id, twilio_call_sid=f"CA-{uuid.uuid4().hex[:12]}", from_number=from_number,
            outcome=CallOutcome.APPOINTMENT_PROPOSED, proposed_appointment_id=appointment_id,
            preferred_contact_channel=channel,
        )
        session.add(call)
        await session.commit()


def _mock_compose():
    return patch(
        "app.services.agents.outbound_agent._compose_message",
        new=AsyncMock(return_value="Your appointment is confirmed for Sept 10 at 10am."),
    )


async def test_confirmation_fails_cleanly_when_outbound_agent_disabled():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with pytest.raises(OutboundAgentNotConfiguredError):
            await outbound_agent.send_appointment_confirmation(db, appointment)


async def test_confirmation_uses_call_preferred_channel_and_logs_sent():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_call(clinic_id, appointment_id, channel=ContactChannel.EMAIL, from_number="+15550001111")
    await _make_outbound_config(clinic_id)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with _mock_compose(), patch(
            "app.services.agents.outbound_agent.send_share_email", return_value="resend-msg-id"
        ) as mock_email:
            log = await outbound_agent.send_appointment_confirmation(db, appointment)

    assert log.status == OutboundMessageStatus.SENT
    assert log.channel == ContactChannel.EMAIL
    assert log.message_type == OutboundMessageType.APPOINTMENT_CONFIRMATION
    assert log.provider_message_id == "resend-msg-id"
    mock_email.assert_called_once()
    assert mock_email.call_args.kwargs["to"] == ["jane@example.com"]


async def test_confirmation_falls_back_to_patient_contact_without_a_call():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_outbound_config(clinic_id)  # no InboundCallSession this time

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with _mock_compose(), patch(
            "app.services.agents.outbound_agent.send_share_email", return_value="resend-msg-id"
        ):
            log = await outbound_agent.send_appointment_confirmation(db, appointment)

    assert log.status == OutboundMessageStatus.SENT
    assert log.channel == ContactChannel.EMAIL


async def test_confirmation_via_sms_requires_a_clinic_phone_number():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, phone="+15550002222")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_call(clinic_id, appointment_id, channel=ContactChannel.SMS, from_number="+15550002222")
    await _make_outbound_config(clinic_id, sms_enabled=True)
    # No InboundAgentConfig at all — no clinic number provisioned.

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with pytest.raises(OutboundAgentNotConfiguredError, match="phone number"):
            await outbound_agent.send_appointment_confirmation(db, appointment)


async def test_confirmation_via_sms_sends_with_clinic_number():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, phone="+15550002222")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_call(clinic_id, appointment_id, channel=ContactChannel.SMS, from_number="+15550002222")
    await _make_outbound_config(clinic_id, sms_enabled=True)
    async with TestSessionLocal() as session:
        session.add(InboundAgentConfig(clinic_id=clinic_id, phone_number="+15559990000"))
        await session.commit()

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with _mock_compose(), patch(
            "app.services.agents.outbound_agent.twilio_client.send_sms", return_value="SM123"
        ) as mock_sms:
            log = await outbound_agent.send_appointment_confirmation(db, appointment)

    assert log.status == OutboundMessageStatus.SENT
    assert log.channel == ContactChannel.SMS
    mock_sms.assert_called_once_with(to="+15550002222", body=log.body_text, from_number="+15559990000")


async def test_confirmation_disabled_channel_raises():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_outbound_config(clinic_id, email_enabled=False)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with pytest.raises(OutboundAgentNotConfiguredError, match="Email"):
            await outbound_agent.send_appointment_confirmation(db, appointment)


async def test_no_contact_channel_on_file_raises():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)  # no email, no phone
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_outbound_config(clinic_id)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with pytest.raises(OutboundAgentNotConfiguredError, match="contact channel"):
            await outbound_agent.send_appointment_confirmation(db, appointment)


async def test_send_failure_is_logged_as_failed_not_raised():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_outbound_config(clinic_id)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with _mock_compose(), patch(
            "app.services.agents.outbound_agent.send_share_email", side_effect=RuntimeError("Resend is down")
        ):
            log = await outbound_agent.send_appointment_confirmation(db, appointment)

    assert log.status == OutboundMessageStatus.FAILED
    assert "Resend is down" in log.error_message


async def test_reminder_uses_reminder_message_type():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id, email="jane@example.com")
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id)
    await _make_outbound_config(clinic_id)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        with _mock_compose(), patch(
            "app.services.agents.outbound_agent.send_share_email", return_value="resend-msg-id"
        ):
            log = await outbound_agent.send_reminder(db, appointment, OutboundMessageType.REMINDER_DAY_BEFORE)

    assert log.message_type == OutboundMessageType.REMINDER_DAY_BEFORE

    async with TestSessionLocal() as db:
        result = await db.execute(select(OutboundMessageLog).where(OutboundMessageLog.id == log.id))
        assert result.scalar_one().appointment_id == appointment_id
