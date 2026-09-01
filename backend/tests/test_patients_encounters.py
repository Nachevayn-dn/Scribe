"""Patient CRUD tests. Encounter tests are added here in Milestone 3."""
from httpx import AsyncClient

from tests.conftest import signup_clinic


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
