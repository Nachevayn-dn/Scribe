"""Doctor-facing call log: list/get role scoping and the one-click
"approve appointment" action (api/calls.py)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from app.models.appointment import Appointment, AppointmentStatus
from app.models.inbound_call_session import CallOutcome, InboundCallSession
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


async def _make_call(
    *, clinic_id: uuid.UUID, provider_id: uuid.UUID | None, patient_id: uuid.UUID | None = None,
    outcome: CallOutcome = CallOutcome.INFO_ONLY, proposed_appointment_id: uuid.UUID | None = None,
) -> uuid.UUID:
    async with TestSessionLocal() as session:
        call = InboundCallSession(
            clinic_id=clinic_id,
            twilio_call_sid=f"CA-{uuid.uuid4().hex[:16]}",
            from_number="+15550001111",
            provider_id=provider_id,
            patient_id=patient_id,
            ended_at=datetime.now(timezone.utc),
            outcome=outcome,
            proposed_appointment_id=proposed_appointment_id,
            transcript_text="Caller: Hi.\nAgent: How can I help?\n",
            summary_text="A caller asked about hours.",
        )
        session.add(call)
        await session.commit()
        await session.refresh(call)
        return call.id


async def _make_proposed_appointment(
    *, clinic_id: uuid.UUID, patient_id: uuid.UUID, provider_id: uuid.UUID
) -> uuid.UUID:
    async with TestSessionLocal() as session:
        appointment = Appointment(
            clinic_id=clinic_id,
            patient_id=patient_id,
            provider_id=provider_id,
            created_by_id=provider_id,
            scheduled_time=datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc),
            reason="implant consultation",
            status=AppointmentStatus.PROPOSED,
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        return appointment.id


async def test_provider_only_sees_own_calls(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")

    call_a = await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider_a["id"]))
    await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider_b["id"]))

    resp = await client.get("/api/v1/calls", headers=provider_a["headers"])
    assert resp.status_code == 200, resp.text
    ids = [c["id"] for c in resp.json()]
    assert ids == [str(call_a)]


async def test_super_admin_sees_all_calls_including_unmatched(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider["id"]))
    await _make_call(clinic_id=clinic_id, provider_id=None)  # no doctor matched at call time

    resp = await client.get("/api/v1/calls", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


async def test_provider_cannot_view_another_providers_call(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")

    call_id = await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider_b["id"]))

    resp = await client.get(f"/api/v1/calls/{call_id}", headers=provider_a["headers"])
    assert resp.status_code == 403


async def test_get_call_includes_transcript_and_summary(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    call_id = await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider["id"]))

    resp = await client.get(f"/api/v1/calls/{call_id}", headers=provider["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary_text"] == "A caller asked about hours."
    assert "How can I help" in body["transcript_text"]


async def test_approve_appointment_flips_status_to_scheduled(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    provider_id = uuid.UUID(provider["id"])
    patient_id = await _make_patient(clinic_id)
    appointment_id = await _make_proposed_appointment(
        clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id
    )
    call_id = await _make_call(
        clinic_id=clinic_id,
        provider_id=provider_id,
        patient_id=patient_id,
        outcome=CallOutcome.APPOINTMENT_PROPOSED,
        proposed_appointment_id=appointment_id,
    )

    resp = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert resp.status_code == 200, resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalar_one()
        assert appointment.status == AppointmentStatus.SCHEDULED


async def test_approve_appointment_triggers_outbound_confirmation(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    provider_id = uuid.UUID(provider["id"])
    patient_id = await _make_patient(clinic_id)
    appointment_id = await _make_proposed_appointment(
        clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id
    )
    call_id = await _make_call(
        clinic_id=clinic_id,
        provider_id=provider_id,
        patient_id=patient_id,
        outcome=CallOutcome.APPOINTMENT_PROPOSED,
        proposed_appointment_id=appointment_id,
    )

    with patch(
        "app.api.calls.outbound_agent.send_appointment_confirmation", new=AsyncMock()
    ) as mock_confirm:
        resp = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert resp.status_code == 200, resp.text
    mock_confirm.assert_called_once()
    assert mock_confirm.call_args.args[1].id == appointment_id


async def test_approve_appointment_succeeds_even_when_outbound_agent_not_configured(client: AsyncClient):
    # No OutboundAgentConfig exists for this clinic — the real (unmocked)
    # send_appointment_confirmation call raises OutboundAgentNotConfiguredError,
    # which approve_appointment must swallow rather than fail the approval on.
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    provider_id = uuid.UUID(provider["id"])
    patient_id = await _make_patient(clinic_id)
    appointment_id = await _make_proposed_appointment(
        clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id
    )
    call_id = await _make_call(
        clinic_id=clinic_id,
        provider_id=provider_id,
        patient_id=patient_id,
        outcome=CallOutcome.APPOINTMENT_PROPOSED,
        proposed_appointment_id=appointment_id,
    )

    resp = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert resp.status_code == 200, resp.text

    async with TestSessionLocal() as session:
        result = await session.execute(select(Appointment).where(Appointment.id == appointment_id))
        assert result.scalar_one().status == AppointmentStatus.SCHEDULED


async def test_approve_appointment_rejects_call_without_a_proposal(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    call_id = await _make_call(
        clinic_id=clinic_id, provider_id=uuid.UUID(provider["id"]), outcome=CallOutcome.INFO_ONLY
    )

    resp = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert resp.status_code == 400


async def test_approve_appointment_is_idempotent_guarded(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    provider_id = uuid.UUID(provider["id"])
    patient_id = await _make_patient(clinic_id)
    appointment_id = await _make_proposed_appointment(
        clinic_id=clinic_id, patient_id=patient_id, provider_id=provider_id
    )
    call_id = await _make_call(
        clinic_id=clinic_id,
        provider_id=provider_id,
        patient_id=patient_id,
        outcome=CallOutcome.APPOINTMENT_PROPOSED,
        proposed_appointment_id=appointment_id,
    )

    first = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert first.status_code == 200

    second = await client.post(f"/api/v1/calls/{call_id}/approve-appointment", headers=provider["headers"])
    assert second.status_code == 400


async def test_dashboard_summary_includes_inbound_calls_this_week(client: AsyncClient):
    admin = await signup_clinic(client)
    clinic_id = await _clinic_id_for(admin["email"])
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider["id"]))
    await _make_call(clinic_id=clinic_id, provider_id=uuid.UUID(provider["id"]))

    resp = await client.get("/api/v1/dashboard/summary", headers=provider["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["inbound_calls_this_week"] == 2
