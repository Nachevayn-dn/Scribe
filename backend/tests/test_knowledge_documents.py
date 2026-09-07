"""Agent knowledge-base documents: upload (with text extraction),
list/filter by agent type, download, retire."""
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
        "/api/v1/platform/clinics", headers=operator_headers, json={"name": "Knowledge Base Test Clinic"}
    )
    return resp.json()["id"]


async def test_upload_and_list_knowledge_documents(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    upload_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents",
        headers=operator["headers"],
        data={"agent_type": "INBOUND", "title": "Services & Pricing"},
        files={"file": ("services.txt", b"Cleaning: $80. Implant consult: $150.", "text/plain")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc = upload_resp.json()
    assert doc["title"] == "Services & Pricing"
    assert doc["agent_type"] == "INBOUND"
    assert doc["has_extracted_text"] is True

    list_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents", headers=operator["headers"]
    )
    assert any(d["id"] == doc["id"] for d in list_resp.json())

    filtered_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents",
        headers=operator["headers"],
        params={"agent_type": "OUTBOUND"},
    )
    assert filtered_resp.json() == []


async def test_download_knowledge_document(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    content = b"Emergency decision tree content here."
    upload_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents",
        headers=operator["headers"],
        data={"agent_type": "INBOUND", "title": "Emergency tree"},
        files={"file": ("tree.txt", content, "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    download_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents/{doc_id}/download",
        headers=operator["headers"],
    )
    assert download_resp.status_code == 200
    assert download_resp.content == content


async def test_retire_knowledge_document(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    upload_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents",
        headers=operator["headers"],
        data={"agent_type": "OUTBOUND", "title": "Implant pre-op instructions"},
        files={"file": ("preop.txt", b"Take antibiotic 2h before.", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents/{doc_id}", headers=operator["headers"]
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents", headers=operator["headers"]
    )
    retired = next(d for d in list_resp.json() if d["id"] == doc_id)
    assert retired["is_active"] is False


async def test_reject_unsupported_file_type(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = await _new_clinic_id(client, operator["headers"])

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/knowledge-documents",
        headers=operator["headers"],
        data={"agent_type": "INBOUND", "title": "Bad file"},
        files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
    )
    assert resp.status_code == 400


async def test_non_platform_admin_cannot_upload(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/platform/clinics/00000000-0000-0000-0000-000000000000/knowledge-documents",
        headers=admin["headers"],
        data={"agent_type": "INBOUND", "title": "x"},
        files={"file": ("x.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 403
