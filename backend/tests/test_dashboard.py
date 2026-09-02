"""Dashboard summary widget counts, and doctor photo upload."""
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


async def test_dashboard_summary_counts_sessions_and_scheduled_ones(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    # One ad-hoc session, one marked as a scheduled appointment.
    resp1 = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    assert resp1.status_code == 201
    resp2 = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={
            "patient_id": patient_id,
            "provider_id": provider["id"],
            "is_scheduled_appointment": True,
            "appointment_time": "2026-09-02T15:00:00Z",
        },
    )
    assert resp2.status_code == 201
    assert resp2.json()["is_scheduled_appointment"] is True

    summary_resp = await client.get("/api/v1/dashboard/summary", headers=provider["headers"])
    assert summary_resp.status_code == 200
    body = summary_resp.json()
    assert body["sessions_this_week"] == 2
    assert body["scheduled_appointment_sessions_this_week"] == 1


async def test_dashboard_summary_scoped_by_provider(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    await client.post(
        "/api/v1/encounters",
        headers=provider_a["headers"],
        json={"patient_id": patient_id, "provider_id": provider_a["id"]},
    )
    await client.post(
        "/api/v1/encounters",
        headers=provider_b["headers"],
        json={"patient_id": patient_id, "provider_id": provider_b["id"]},
    )

    resp_a = await client.get("/api/v1/dashboard/summary", headers=provider_a["headers"])
    assert resp_a.json()["sessions_this_week"] == 1

    resp_admin = await client.get("/api/v1/dashboard/summary", headers=admin["headers"])
    assert resp_admin.json()["sessions_this_week"] == 2


async def test_upload_my_photo(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    tiny_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6360000002000100e02186c4000000"
        "0049454e44ae426082"
    )
    resp = await client.post(
        "/api/v1/users/me/photo",
        headers=provider["headers"],
        files={"file": ("avatar.png", tiny_png, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    photo_url = resp.json()["photo_url"]
    assert photo_url is not None
    assert photo_url.startswith("/static/avatars/")

    me_resp = await client.get("/api/v1/auth/me", headers=provider["headers"])
    assert me_resp.json()["photo_url"] == photo_url


async def test_upload_my_photo_rejects_unsupported_type(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.post(
        "/api/v1/users/me/photo",
        headers=provider["headers"],
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 400
