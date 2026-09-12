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


async def test_clinic_creation_accepts_contact_and_notification_emails(client: AsyncClient):
    """The 'New clinic' form's confirmation summary (name/email/notification
    email/phone) is only meaningful if these are actually persisted at
    creation time, not just editable afterwards via PATCH."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    resp = await client.post(
        "/api/v1/platform/clinics",
        headers=operator["headers"],
        json={
            "name": "Lakeside Pediatrics",
            "phone": "555-0177",
            "contact_email": "hello@lakeside.example",
            "staff_email": "frontdesk@lakeside.example",
        },
    )
    assert resp.status_code == 201, resp.text
    clinic = resp.json()
    assert clinic["contact_email"] == "hello@lakeside.example"
    assert clinic["staff_email"] == "frontdesk@lakeside.example"

    # And it's really saved, not just echoed — a fresh fetch shows the same.
    list_resp = await client.get("/api/v1/platform/clinics", headers=operator["headers"])
    saved = next(c for c in list_resp.json() if c["id"] == clinic["id"])
    assert saved["contact_email"] == "hello@lakeside.example"
    assert saved["staff_email"] == "frontdesk@lakeside.example"


async def test_platform_admin_can_set_and_clear_clinic_branding(client: AsyncClient):
    """White-label override: only reachable via the platform console
    (require_platform_admin), never via a clinic's own SUPER_ADMIN role —
    see test_clinic_super_admin_cannot_set_own_branding below."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    create_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Willow Creek Dental"}
    )
    clinic_id = create_resp.json()["id"]
    assert create_resp.json()["logo_url"] is None
    assert create_resp.json()["branding_name"] is None

    # Set a custom wordmark.
    patch_resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}",
        headers=operator["headers"],
        json={"branding_name": "Willow Creek Dental Care"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["branding_name"] == "Willow Creek Dental Care"

    # Upload a logo.
    tiny_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6360000002000100e02186c4000000"
        "0049454e44ae426082"
    )
    logo_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/logo",
        headers=operator["headers"],
        files={"file": ("logo.png", tiny_png, "image/png")},
    )
    assert logo_resp.status_code == 200, logo_resp.text
    logo_url = logo_resp.json()["logo_url"]
    assert logo_url is not None
    assert logo_url.startswith("/static/clinic-logos/")

    # A doctor at that clinic sees the override denormalized onto their own
    # /auth/me response — the nav bar needs it without a second request.
    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "willow-doc@example.com", "full_name": "Dr. Willow", "role": "PROVIDER"},
    )
    doctor_id = doctor_resp.json()["id"]
    creds_resp = await client.post(
        f"/api/v1/platform/users/{doctor_id}/generate-credentials", headers=operator["headers"]
    )
    temp_password = creds_resp.json()["temp_password"]
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "willow-doc@example.com", "password": temp_password}
    )
    doctor_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    me_resp = await client.get("/api/v1/auth/me", headers=doctor_headers)
    assert me_resp.json()["clinic_branding_name"] == "Willow Creek Dental Care"
    assert me_resp.json()["clinic_logo_url"] == logo_url

    # Clear both back to the default.
    clear_resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}",
        headers=operator["headers"],
        json={"branding_name": None},
    )
    assert clear_resp.json()["branding_name"] is None

    delete_resp = await client.delete(f"/api/v1/platform/clinics/{clinic_id}/logo", headers=operator["headers"])
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["logo_url"] is None


async def test_clinic_super_admin_cannot_set_own_branding(client: AsyncClient):
    """Branding is a platform-operator decision, not a clinic self-service
    setting — a clinic's own SUPER_ADMIN has no route to it at all."""
    admin = await signup_clinic(client)
    me_resp = await client.get("/api/v1/auth/me", headers=admin["headers"])
    clinic_id = me_resp.json()["clinic_id"]

    resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/logo",
        headers=admin["headers"],
        files={"file": ("logo.png", b"not-a-real-png", "image/png")},
    )
    assert resp.status_code == 403


async def test_platform_admin_can_update_clinic_details(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    create_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Original Name"}
    )
    clinic_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}",
        headers=operator["headers"],
        json={"contact_email": "clinic@example.com", "staff_email": "frontdesk@example.com"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["contact_email"] == "clinic@example.com"
    assert body["staff_email"] == "frontdesk@example.com"
    assert body["name"] == "Original Name"  # untouched field stays as-is


async def test_updating_one_clinics_email_does_not_affect_another(client: AsyncClient):
    """The exact scenario a platform admin managing multiple clinics needs
    guaranteed: each clinic's email is its own row, fully independent."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    clinic_a = (
        await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Clinic A"})
    ).json()
    clinic_b = (
        await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Clinic B"})
    ).json()

    await client.patch(
        f"/api/v1/platform/clinics/{clinic_a['id']}",
        headers=operator["headers"],
        json={"contact_email": "a@example.com"},
    )
    await client.patch(
        f"/api/v1/platform/clinics/{clinic_b['id']}",
        headers=operator["headers"],
        json={"contact_email": "b@example.com"},
    )

    list_resp = await client.get("/api/v1/platform/clinics", headers=operator["headers"])
    by_id = {c["id"]: c for c in list_resp.json()}
    assert by_id[clinic_a["id"]]["contact_email"] == "a@example.com"
    assert by_id[clinic_b["id"]]["contact_email"] == "b@example.com"


async def test_update_clinic_requires_platform_admin(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_id = (
        await client.post("/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Some Clinic"})
    ).json()["id"]

    outsider = await signup_clinic(client)  # not a platform admin
    resp = await client.patch(
        f"/api/v1/platform/clinics/{clinic_id}", headers=outsider["headers"], json={"contact_email": "x@example.com"}
    )
    assert resp.status_code == 403


async def test_update_nonexistent_clinic_404s(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    resp = await client.patch(
        "/api/v1/platform/clinics/00000000-0000-0000-0000-000000000000",
        headers=operator["headers"],
        json={"contact_email": "x@example.com"},
    )
    assert resp.status_code == 404


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


async def test_send_setup_link_lets_doctor_set_own_password(client: AsyncClient):
    """The preferred flow now: instead of the admin generating and relaying
    a temp password, the doctor gets a link and picks her own."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])

    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Link Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]

    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "linkdoc@example.com", "full_name": "Dr. Link", "role": "PROVIDER"},
    )
    doctor_id = doctor_resp.json()["id"]

    link_resp = await client.post(
        f"/api/v1/platform/users/{doctor_id}/send-setup-link",
        headers=operator["headers"],
        params={"send_email": "false"},
    )
    assert link_resp.status_code == 200, link_resp.text
    body = link_resp.json()
    assert body["emailed"] is False
    assert "/set-password?token=" in body["setup_url"]
    token = body["setup_url"].rsplit("token=", 1)[-1]

    # The link's own page can look up whose password this is before
    # showing the form.
    info_resp = await client.get(f"/api/v1/auth/setup-token/{token}")
    assert info_resp.status_code == 200, info_resp.text
    assert info_resp.json() == {"email": "linkdoc@example.com", "full_name": "Dr. Link"}

    set_resp = await client.post(
        "/api/v1/auth/set-password", json={"token": token, "password": "her-own-password-1"}
    )
    assert set_resp.status_code == 200, set_resp.text
    assert "access_token" in set_resp.json()  # logged straight in

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "linkdoc@example.com", "password": "her-own-password-1"}
    )
    assert login_resp.status_code == 200, login_resp.text

    # Single-use — the same link cannot be replayed.
    replay_resp = await client.post(
        "/api/v1/auth/set-password", json={"token": token, "password": "someone-elses-password"}
    )
    assert replay_resp.status_code == 400


async def test_setup_link_reports_email_failure_but_still_returns_url(client: AsyncClient):
    """No RESEND_API_KEY in the test environment — emailing fails, but the
    link itself is still usable (same fallback as generate-credentials)."""
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Email Fail Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]
    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "noemail@example.com", "full_name": "Dr. NoEmail", "role": "PROVIDER"},
    )
    doctor_id = doctor_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/platform/users/{doctor_id}/send-setup-link", headers=operator["headers"]
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["emailed"] is False
    assert body["email_error"] is not None
    assert body["setup_url"]


async def test_unknown_or_garbage_setup_token_is_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/auth/setup-token/not-a-real-token")
    assert resp.status_code == 400
    resp2 = await client.post(
        "/api/v1/auth/set-password", json={"token": "not-a-real-token", "password": "whatever1234"}
    )
    assert resp2.status_code == 400


async def test_resending_setup_link_invalidates_the_previous_one(client: AsyncClient):
    operator = await signup_clinic(client)
    await _make_platform_admin(operator["email"])
    clinic_resp = await client.post(
        "/api/v1/platform/clinics", headers=operator["headers"], json={"name": "Resend Clinic"}
    )
    clinic_id = clinic_resp.json()["id"]
    doctor_resp = await client.post(
        f"/api/v1/platform/clinics/{clinic_id}/doctors",
        headers=operator["headers"],
        json={"email": "resend@example.com", "full_name": "Dr. Resend", "role": "PROVIDER"},
    )
    doctor_id = doctor_resp.json()["id"]

    first = await client.post(
        f"/api/v1/platform/users/{doctor_id}/send-setup-link",
        headers=operator["headers"],
        params={"send_email": "false"},
    )
    first_token = first.json()["setup_url"].rsplit("token=", 1)[-1]

    second = await client.post(
        f"/api/v1/platform/users/{doctor_id}/send-setup-link",
        headers=operator["headers"],
        params={"send_email": "false"},
    )
    second_token = second.json()["setup_url"].rsplit("token=", 1)[-1]
    assert first_token != second_token

    stale_resp = await client.get(f"/api/v1/auth/setup-token/{first_token}")
    assert stale_resp.status_code == 400

    fresh_resp = await client.get(f"/api/v1/auth/setup-token/{second_token}")
    assert fresh_resp.status_code == 200


async def test_send_setup_link_requires_platform_admin(client: AsyncClient):
    non_admin = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/platform/users/00000000-0000-0000-0000-000000000000/send-setup-link",
        headers=non_admin["headers"],
    )
    assert resp.status_code == 403


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
