"""Platform admin console: clinic creation, doctor pre-provisioning (no
password until credentials are generated), document upload/download, and
access gating — a clinic's own SUPER_ADMIN has none of this access."""
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


async def test_regular_super_admin_cannot_access_platform_console(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.get("/api/v1/platform/clinics", headers=admin["headers"])
    assert resp.status_code == 403


async def test_platform_admin_can_create_clinic(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    resp = await client.post(
        "/api/v1/platform/clinics",
        headers=operator["headers"],
        json={"name": "Riverside Family Medicine", "address": "1 Main St", "phone": "555-0100"},
    )
    assert resp.status_code == 201, resp.text
    clinic = resp.json()
    assert clinic["name"] == "Riverside Family Medicine"

    list_resp = await client.get("/api/v1/platform/clinics", headers=operator["headers"])
    assert any(c["id"] == clinic["id"] for c in list_resp.json())


async def test_provision_doctor_then_generate_credentials(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Test Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]

    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "newdoc@example.com", "full_name": "Dr. New", "role": "PROVIDER"},
    )
    assert doctor_resp.status_code == 201, doctor_resp.text
    doctor = doctor_resp.json()
    assert doctor["password_set_at"] is None

    # No credentials yet — cannot log in with any password.
    login_attempt = await client.post(
        "/api/v1/auth/login", json={"email": "newdoc@example.com", "password": "anything12345"}
    )
    assert login_attempt.status_code == 401

    listed = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/doctors", headers=operator["headers"]
    )
    assert any(d["id"] == doctor["id"] for d in listed.json())

    creds_resp = await client.post(
        f"/api/v1/platform/users/{doctor['id']}/generate-credentials",
        headers=operator["headers"],
    )
    assert creds_resp.status_code == 200, creds_resp.text
    temp_password = creds_resp.json()["temp_password"]
    assert len(temp_password) >= 8
    assert creds_resp.json()["emailed"] is False  # send_email not requested

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "newdoc@example.com", "password": temp_password}
    )
    assert login_resp.status_code == 200, login_resp.text


async def test_upload_and_download_clinic_document(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Doc Test Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]

    pdf_bytes = b"%PDF-1.4 fake contract content"
    upload_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/documents",
        headers=operator["headers"],
        data={"doc_type": "CONTRACT"},
        files={"file": ("contract.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document = upload_resp.json()
    assert document["doc_type"] == "CONTRACT"
    assert document["original_filename"] == "contract.pdf"

    list_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/documents", headers=operator["headers"]
    )
    assert any(d["id"] == document["id"] for d in list_resp.json())

    download_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/documents/{document['id']}/download",
        headers=operator["headers"],
    )
    assert download_resp.status_code == 200
    assert download_resp.content == pdf_bytes


async def test_document_upload_rejects_unsupported_type(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Doc Reject Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/documents",
        headers=operator["headers"],
        data={"doc_type": "CONSENT_FORM"},
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert resp.status_code == 400


async def test_platform_admin_can_drill_into_clinic_patients_and_sessions(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Drilldown Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]

    patients_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/patients", headers=operator["headers"]
    )
    assert patients_resp.status_code == 200
    assert patients_resp.json() == []

    encounters_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/encounters", headers=operator["headers"]
    )
    assert encounters_resp.status_code == 200
    assert encounters_resp.json() == []


async def test_platform_analytics_counts_clinics(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Analytics Clinic"})

    resp = await client.get("/api/v1/platform/analytics", headers=operator["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["clinics_count"] >= 2  # the operator's own clinic + the new one
