"""Appointment scheduling: create/list/cancel, role-scoping, cross-clinic isolation."""
from httpx import AsyncClient

from tests.conftest import create_user, signup_clinic


async def _create_patient(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-01"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_provider_can_schedule_own_appointment(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/appointments",
        headers=provider["headers"],
        json={
            "patient_id": patient_id,
            "provider_id": provider["id"],
            "scheduled_time": "2026-09-20T15:00:00Z",
            "reason": "Follow-up in two weeks",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "SCHEDULED"
    assert body["reason"] == "Follow-up in two weeks"


async def test_provider_cannot_schedule_for_another_provider(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/appointments",
        headers=provider_a["headers"],
        json={
            "patient_id": patient_id,
            "provider_id": provider_b["id"],
            "scheduled_time": "2026-09-20T15:00:00Z",
        },
    )
    assert resp.status_code == 403


async def test_appointments_scoped_by_provider(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    await client.post(
        "/api/v1/appointments",
        headers=provider_a["headers"],
        json={"patient_id": patient_id, "provider_id": provider_a["id"], "scheduled_time": "2026-09-20T15:00:00Z"},
    )
    await client.post(
        "/api/v1/appointments",
        headers=provider_b["headers"],
        json={"patient_id": patient_id, "provider_id": provider_b["id"], "scheduled_time": "2026-09-21T15:00:00Z"},
    )

    list_a = await client.get("/api/v1/appointments", headers=provider_a["headers"])
    assert len(list_a.json()) == 1

    list_admin = await client.get("/api/v1/appointments", headers=admin["headers"])
    assert len(list_admin.json()) == 2


async def test_cross_clinic_isolation(client: AsyncClient):
    admin1 = await signup_clinic(client)
    provider1 = await create_user(client, admin1["headers"], role="PROVIDER")
    patient1 = await _create_patient(client, admin1["headers"])
    resp = await client.post(
        "/api/v1/appointments",
        headers=provider1["headers"],
        json={"patient_id": patient1, "provider_id": provider1["id"], "scheduled_time": "2026-09-20T15:00:00Z"},
    )
    appointment_id = resp.json()["id"]

    admin2 = await signup_clinic(client)
    list_resp = await client.get("/api/v1/appointments", headers=admin2["headers"])
    assert list_resp.json() == []

    patch_resp = await client.patch(
        f"/api/v1/appointments/{appointment_id}",
        headers=admin2["headers"],
        json={"status": "CANCELLED"},
    )
    assert patch_resp.status_code == 404


async def test_cancel_appointment(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])
    resp = await client.post(
        "/api/v1/appointments",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"], "scheduled_time": "2026-09-20T15:00:00Z"},
    )
    appointment_id = resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/appointments/{appointment_id}",
        headers=provider["headers"],
        json={"status": "CANCELLED"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "CANCELLED"


async def test_dashboard_upcoming_appointments_widget(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    from datetime import datetime, timedelta, timezone

    in_3_days = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    in_30_days = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    await client.post(
        "/api/v1/appointments",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"], "scheduled_time": in_3_days},
    )
    # Outside the 7-day window — should not count.
    await client.post(
        "/api/v1/appointments",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"], "scheduled_time": in_30_days},
    )

    summary_resp = await client.get("/api/v1/dashboard/summary", headers=provider["headers"])
    assert summary_resp.status_code == 200
    assert summary_resp.json()["upcoming_appointments"] == 1
