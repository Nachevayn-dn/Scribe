"""services/reminder_scheduler.py: due-detection for the day-before/
hours-before pre-procedure check-ins, and the idempotency stamp that stops
a misconfigured clinic from being retried forever."""
import uuid
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic import Clinic
from app.models.outbound_agent_config import OutboundAgentConfig
from app.models.outbound_message_log import OutboundMessageType
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.services import reminder_scheduler
from tests.conftest import TestSessionLocal


async def _make_clinic() -> uuid.UUID:
    async with TestSessionLocal() as session:
        clinic = Clinic(name=f"Scheduler Test Clinic {uuid.uuid4().hex[:8]}")
        session.add(clinic)
        await session.commit()
        await session.refresh(clinic)
        return clinic.id


async def _make_provider(clinic_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        user = User(
            clinic_id=clinic_id, email=f"doc-{uuid.uuid4().hex[:8]}@example.com",
            full_name="Dr. Scheduler Test", role=UserRole.PROVIDER, hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _make_patient(clinic_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        patient = Patient(
            clinic_id=clinic_id, first_name="Jane", last_name="Doe",
            date_of_birth=datetime(1985, 4, 12).date(), email="jane@example.com",
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient.id


async def _make_appointment(
    clinic_id: uuid.UUID, patient_id: uuid.UUID, provider_id: uuid.UUID, scheduled_time: datetime, **overrides
) -> uuid.UUID:
    overrides.setdefault("status", AppointmentStatus.SCHEDULED)
    async with TestSessionLocal() as session:
        appointment = Appointment(
            clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id, created_by_id=provider_id,
            scheduled_time=scheduled_time, **overrides,
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        return appointment.id


async def _make_outbound_config(clinic_id: uuid.UUID, **overrides) -> None:
    overrides.setdefault("enabled", True)
    async with TestSessionLocal() as session:
        config = OutboundAgentConfig(clinic_id=clinic_id, **overrides)
        session.add(config)
        await session.commit()


async def test_hours_before_reminder_is_due_and_stamped():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    soon = datetime.now(timezone.utc) + timedelta(hours=1)
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id, soon)
    await _make_outbound_config(clinic_id, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[2] == OutboundMessageType.REMINDER_HOURS_BEFORE

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        assert appointment.reminder_hours_before_sent_at is not None
        assert appointment.reminder_day_before_sent_at is None


async def test_hours_before_reminder_not_yet_due_is_skipped():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    far_off = datetime.now(timezone.utc) + timedelta(hours=10)
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id, far_off)
    await _make_outbound_config(clinic_id, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_not_called()

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        assert appointment.reminder_hours_before_sent_at is None


async def test_already_sent_hours_before_reminder_is_not_resent():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    soon = datetime.now(timezone.utc) + timedelta(hours=1)
    appointment_id = await _make_appointment(
        clinic_id, patient_id, provider_id, soon, reminder_hours_before_sent_at=datetime.now(timezone.utc)
    )
    await _make_outbound_config(clinic_id, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_not_called()


async def test_day_before_reminder_due_after_send_hour():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1, hours=3)
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id, tomorrow)
    await _make_outbound_config(
        clinic_id, day_before_enabled=True, day_before_send_hour=time(0, 0), hours_before_enabled=False
    )

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[2] == OutboundMessageType.REMINDER_DAY_BEFORE

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        assert appointment.reminder_day_before_sent_at is not None


async def test_day_before_reminder_before_send_hour_is_skipped():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1, hours=3)
    await _make_appointment(clinic_id, patient_id, provider_id, tomorrow)
    # A send hour so late in the day it hasn't arrived yet "today", whatever
    # time this test happens to run.
    await _make_outbound_config(
        clinic_id, day_before_enabled=True, day_before_send_hour=time(23, 59), hours_before_enabled=False
    )

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_not_called()


async def test_cancelled_appointment_is_never_reminded():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    soon = datetime.now(timezone.utc) + timedelta(hours=1)
    await _make_appointment(
        clinic_id, patient_id, provider_id, soon, status=AppointmentStatus.CANCELLED
    )
    await _make_outbound_config(clinic_id, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
        ) as mock_send:
            await reminder_scheduler._sweep_clinic(db, config)

    mock_send.assert_not_called()


async def test_send_failure_still_stamps_to_avoid_retry_loop():
    clinic_id = await _make_clinic()
    provider_id = await _make_provider(clinic_id)
    patient_id = await _make_patient(clinic_id)
    soon = datetime.now(timezone.utc) + timedelta(hours=1)
    appointment_id = await _make_appointment(clinic_id, patient_id, provider_id, soon)
    await _make_outbound_config(clinic_id, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)

    async with TestSessionLocal() as db:
        config = (
            await db.execute(select(OutboundAgentConfig).where(OutboundAgentConfig.clinic_id == clinic_id))
        ).scalar_one()
        with patch(
            "app.services.reminder_scheduler.outbound_agent.send_reminder",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await reminder_scheduler._sweep_clinic(db, config)

    async with TestSessionLocal() as db:
        appointment = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one()
        assert appointment.reminder_hours_before_sent_at is not None


async def test_run_reminder_sweep_only_visits_enabled_clinics():
    enabled_clinic = await _make_clinic()
    disabled_clinic = await _make_clinic()
    provider_id = await _make_provider(enabled_clinic)
    patient_id = await _make_patient(enabled_clinic)
    soon = datetime.now(timezone.utc) + timedelta(hours=1)
    await _make_appointment(enabled_clinic, patient_id, provider_id, soon)
    await _make_outbound_config(enabled_clinic, hours_before_enabled=True, hours_before_offset=2, day_before_enabled=False)
    await _make_outbound_config(disabled_clinic, enabled=False)

    with patch(
        "app.services.reminder_scheduler.outbound_agent.send_reminder", new=AsyncMock()
    ) as mock_send, patch("app.services.reminder_scheduler.AsyncSessionLocal", TestSessionLocal):
        await reminder_scheduler.run_reminder_sweep()

    mock_send.assert_called_once()
