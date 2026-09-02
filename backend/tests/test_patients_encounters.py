"""Patient CRUD tests, plus encounter creation/access-control tests."""
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


async def test_patient_crud(client: AsyncClient):
    admin = await signup_clinic(client)

    create_resp = await client.post(
        "/api/v1/patients",
        headers=admin["headers"],
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "mrn": "MRN-001",
        },
    )
    assert create_resp.status_code == 201
    patient = create_resp.json()
    assert patient["first_name"] == "Jane"

    get_resp = await client.get(f"/api/v1/patients/{patient['id']}", headers=admin["headers"])
    assert get_resp.status_code == 200

    list_resp = await client.get("/api/v1/patients", headers=admin["headers"])
    assert list_resp.status_code == 200
    assert any(p["id"] == patient["id"] for p in list_resp.json())

    update_resp = await client.patch(
        f"/api/v1/patients/{patient['id']}",
        headers=admin["headers"],
        json={"phone": "555-0100"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["phone"] == "555-0100"


async def test_get_nonexistent_patient_404s(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.get(
        "/api/v1/patients/00000000-0000-0000-0000-000000000000", headers=admin["headers"]
    )
    assert resp.status_code == 404


async def test_patients_require_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/patients")
    assert resp.status_code == 401


async def test_provider_can_start_encounter_for_self(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["provider_id"] == provider["id"]
    assert body["language"] is None  # omitted -> auto-detect


async def test_start_encounter_persists_chosen_language(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/encounters",
        headers=provider["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"], "language": "bg"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["language"] == "bg"

    get_resp = await client.get(
        f"/api/v1/encounters/{resp.json()['id']}", headers=provider["headers"]
    )
    assert get_resp.json()["language"] == "bg"


async def test_provider_cannot_start_encounter_for_another_provider(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/encounters",
        headers=provider_a["headers"],
        json={"patient_id": patient_id, "provider_id": provider_b["id"]},
    )
    assert resp.status_code == 403


async def test_unassigned_assistant_cannot_start_encounter(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")
    patient_id = await _create_patient(client, admin["headers"])

    resp = await client.post(
        "/api/v1/encounters",
        headers=assistant["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    assert resp.status_code == 403


async def test_assigned_assistant_can_start_and_access_encounter(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")
    patient_id = await _create_patient(client, admin["headers"])

    assign = await client.post(
        f"/api/v1/users/{provider['id']}/assistants/{assistant['id']}",
        headers=admin["headers"],
    )
    assert assign.status_code == 201

    resp = await client.post(
        "/api/v1/encounters",
        headers=assistant["headers"],
        json={"patient_id": patient_id, "provider_id": provider["id"]},
    )
    assert resp.status_code == 201, resp.text
    encounter_id = resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/encounters/{encounter_id}", headers=assistant["headers"]
    )
    assert get_resp.status_code == 200

    # A different, unassigned assistant must not be able to read it.
    other_assistant = await create_user(client, admin["headers"], role="ASSISTANT")
    forbidden = await client.get(
        f"/api/v1/encounters/{encounter_id}", headers=other_assistant["headers"]
    )
    assert forbidden.status_code == 403


async def test_list_encounters_scoped_by_role(client: AsyncClient):
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

    resp = await client.get("/api/v1/encounters", headers=provider_a["headers"])
    assert resp.status_code == 200
    encounters = resp.json()
    assert len(encounters) == 1
    assert encounters[0]["provider_id"] == provider_a["id"]

    resp = await client.get("/api/v1/encounters", headers=admin["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
