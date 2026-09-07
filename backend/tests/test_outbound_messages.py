"""Doctor-facing outbound message log (api/outbound_messages.py): role
scoping via the linked appointment's provider, same shape as calls.py."""
import uuid
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent_common import ContactChannel
from app.models.appointment import Appointment, AppointmentStatus
from app.models.outbound_message_log import OutboundMessageLog, OutboundMessageStatus, OutboundMessageType
from app.models.patient import Patient
from app.models.user import User
from tests.conftest import TestSessionLocal, create_user, signup_clinic


async def _clinic_id_for(email: str) -> uuid.UUID:
    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one().clinic_id


async def _make_patient(clinic_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        patient = Patient(
            clinic_id=clinic_id, first_name="Jane", last_name="Doe", date_of_birth=datetime(1985, 4, 12).date()
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient.id


async def _make_appointment(clinic_id: uuid.UUID, patient_id: uuid.UUID, provider_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        appointment = Appointment(
            clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id, created_by_id=provider_id,
            scheduled_time=datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc), status=AppointmentStatus.SCHEDULED,
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        return appointment.id


async def _make_message(
    clinic_id: uuid.UUID, patient_id: uuid.UUID, appointment_id: uuid.UUID | None
) -> None:
    async with TestSessionLocal() as session:
        session.add(
            OutboundMessageLog(
                clinic_id=clinic_id, appointment_id=appointment_id, patient_id=patient_id,
                channel=ContactChannel.EMAIL, message_type=OutboundMessageType.APPOINTMENT_CONFIRMATION,
                body_text="You're confirmed for Sept 10.", status=OutboundMessageStatus.SENT,
            )
        )
        await session.commit()


async def test_provider_only_sees_messages_for_own_appointments(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _make_patient(clinic_id)

    appt_a = await _make_appointment(clinic_id, patient_id, uuid.UUID(provider_a["id"]))
    appt_b = await _make_appointment(clinic_id, patient_id, uuid.UUID(provider_b["id"]))
    await _make_message(clinic_id, patient_id, appt_a)
    await _make_message(clinic_id, patient_id, appt_b)

    resp = await client.get("/api/v1/outbound-messages", headers=provider_a["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["appointment_id"] == str(appt_a)


async def test_super_admin_sees_messages_with_no_appointment_link(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    patient_id = await _make_patient(clinic_id)
    await _make_message(clinic_id, patient_id, None)

    resp = await client.get("/api/v1/outbound-messages", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    assert resp.json()[0]["appointment_id"] is None


async def test_provider_does_not_see_messages_with_no_appointment_link(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _make_patient(clinic_id)
    await _make_message(clinic_id, patient_id, None)

    resp = await client.get("/api/v1/outbound-messages", headers=provider["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
