from httpx import AsyncClient

from tests.conftest import create_user, signup_clinic


async def test_only_super_admin_can_create_users(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.post(
        "/api/v1/users",
        headers=provider["headers"],
        json={
            "email": "someone@example.com",
            "password": "supersecret1",
            "full_name": "Nope",
            "role": "ASSISTANT",
        },
    )
    assert resp.status_code == 403


async def test_only_super_admin_can_list_users(client: AsyncClient):
    admin = await signup_clinic(client)
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")

    resp = await client.get("/api/v1/users", headers=assistant["headers"])
    assert resp.status_code == 403

    resp = await client.get("/api/v1/users", headers=admin["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) >= 2  # admin + assistant


async def test_assistant_provider_assignment_flow(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")

    resp = await client.post(
        f"/api/v1/users/{provider['id']}/assistants/{assistant['id']}",
        headers=admin["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "assigned"

    # Assigning again is idempotent, not an error.
    resp = await client.post(
        f"/api/v1/users/{provider['id']}/assistants/{assistant['id']}",
        headers=admin["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "already_assigned"

    resp = await client.delete(
        f"/api/v1/users/{provider['id']}/assistants/{assistant['id']}",
        headers=admin["headers"],
    )
    assert resp.status_code == 204


async def test_assign_rejects_wrong_roles(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    another_provider = await create_user(client, admin["headers"], role="PROVIDER")

    # provider_id must actually be a PROVIDER, assistant_id must be an ASSISTANT
    resp = await client.post(
        f"/api/v1/users/{provider['id']}/assistants/{another_provider['id']}",
        headers=admin["headers"],
    )
    assert resp.status_code == 409


async def test_cross_clinic_isolation(client: AsyncClient):
    clinic_a = await signup_clinic(client, clinic_name="Clinic A")
    clinic_b = await signup_clinic(client, clinic_name="Clinic B")

    patient_resp = await client.post(
        "/api/v1/patients",
        headers=clinic_a["headers"],
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-01"},
    )
    assert patient_resp.status_code == 201
    patient_id = patient_resp.json()["id"]

    # Clinic B must not be able to see Clinic A's patient.
    resp = await client.get(f"/api/v1/patients/{patient_id}", headers=clinic_b["headers"])
    assert resp.status_code == 404

    resp = await client.get("/api/v1/patients", headers=clinic_b["headers"])
    assert resp.status_code == 200
    assert all(p["id"] != patient_id for p in resp.json())


async def test_all_roles_can_manage_patients(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")

    for actor in (admin, provider, assistant):
        resp = await client.post(
            "/api/v1/patients",
            headers=actor["headers"],
            json={"first_name": "Pat", "last_name": "Ient", "date_of_birth": "1985-05-05"},
        )
        assert resp.status_code == 201, resp.text
