"""Agent decision rules: create/list/update/delete, clinic-wide vs
per-provider scoping, platform-admin gating."""
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
        "/api/v1/platform/clinics", headers=operator_headers, json={"name": "Decision Rules Test Clinic"}
    )
    return resp.json()["id"]


async def test_create_and_list_clinic_wide_rule(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        json={
            "condition": "Caller describes chest pain or difficulty breathing",
            "action": "Stop scheduling. Tell them to hang up and call emergency services.",
            "priority": 0,
        },
    )
    assert resp.status_code == 201, resp.text
    rule = resp.json()
    assert rule["provider_id"] is None
    assert rule["is_active"] is True

    list_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules", headers=operator["headers"]
    )
    assert any(r["id"] == rule["id"] for r in list_resp.json())


async def test_provider_scoped_rule_visible_with_clinic_wide(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])
    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "dr-rules@example.com", "full_name": "Dr. Rules", "role": "PROVIDER"},
    )
    provider_id = doctor_resp.json()["id"]

    await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        json={"condition": "Clinic-wide rule", "action": "Do X"},
    )
    await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        json={"condition": "Dr. Rules only", "action": "Do Y", "provider_id": provider_id},
    )
    # A different (nonexistent) provider's view shouldn't see Dr. Rules' rule.
    other_provider_view = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        params={"provider_id": "00000000-0000-0000-0000-000000000000"},
    )
    conditions = [r["condition"] for r in other_provider_view.json()]
    assert "Clinic-wide rule" in conditions
    assert "Dr. Rules only" not in conditions

    this_provider_view = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        params={"provider_id": provider_id},
    )
    conditions = [r["condition"] for r in this_provider_view.json()]
    assert "Clinic-wide rule" in conditions
    assert "Dr. Rules only" in conditions


async def test_update_and_delete_rule(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    create_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules",
        headers=operator["headers"],
        json={"condition": "Original", "action": "Do something"},
    )
    rule_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules/{rule_id}",
        headers=operator["headers"],
        json={"condition": "Updated condition", "is_active": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["condition"] == "Updated condition"
    assert update_resp.json()["is_active"] is False

    delete_resp = await client.delete(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules/{rule_id}", headers=operator["headers"]
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/decision-rules", headers=operator["headers"]
    )
    assert all(r["id"] != rule_id for r in list_resp.json())


async def test_non_platform_admin_cannot_manage_rules(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/platform/clinics/00000000-0000-0000-0000-000000000000/decision-rules",
        headers=admin["headers"],
        json={"condition": "x", "action": "y"},
    )
    assert resp.status_code == 403
