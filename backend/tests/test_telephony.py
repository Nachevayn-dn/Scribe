"""Telephony (Twilio) config: get/patch, platform-admin gating, and a clean
error (not a crash) when Twilio credentials aren't configured."""
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from tests.conftest import TestSessionLocal, signup_clinic


async def _make_platform_admin(email: str) -> None:
    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_platform_admin = True
        await session.commit()


async def _new_clinic_id(client: AsyncClient, operator_headers: dict) -> str:
    resp = await client.post(
        "/api/v1/platform/clinics", headers=operator_headers, json={"name": "Telephony Test Clinic"}
    )
    return resp.json()["id"]


async def test_non_platform_admin_cannot_access_telephony(client: AsyncClient):
    admin = await signup_clinic(client)
    # The require_platform_admin gate runs before the clinic is even looked
    # up, so any syntactically valid UUID trips it.
    resp = await client.get(
        "/api/v1/platform/clinics/00000000-0000-0000-0000-000000000000/telephony",
        headers=admin["headers"],
    )
    assert resp.status_code == 403


async def test_get_telephony_config_creates_default(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.get(f"/api/v1/platform/clinics/{clinic_id}/telephony", headers=operator["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enabled"] is False
    assert body["phone_number"] is None
    assert body["pickup_mode"] == "ALWAYS"
    assert body["default_language"] == "en"
    assert body["additional_languages"] == []


async def test_update_telephony_config(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}/telephony",
        headers=operator["headers"],
        json={
            "enabled": True,
            "pickup_mode": "AFTER_HOURS",
            "after_hours_start": "17:00:00",
            "after_hours_end": "09:00:00",
            "forward_to_number": "+15551234567",
            "additional_languages": ["es", "fr"],
            "greeting_text": "Welcome to Riverside Clinic!",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enabled"] is True
    assert body["pickup_mode"] == "AFTER_HOURS"
    assert body["after_hours_start"] == "17:00:00"
    assert body["forward_to_number"] == "+15551234567"
    assert body["additional_languages"] == ["es", "fr"]
    assert body["greeting_text"] == "Welcome to Riverside Clinic!"


async def test_provision_number_without_twilio_credentials_is_clean_400(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/telephony/provision-number", headers=operator["headers"]
    )
    assert resp.status_code == 400
    assert "Twilio" in resp.json()["detail"]


async def test_connect_whatsapp_sandbox_default(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/telephony/whatsapp/connect",
        headers=operator["headers"],
        json={},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["whatsapp_number"] == "whatsapp:+14155238886"
