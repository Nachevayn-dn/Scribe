from httpx import AsyncClient

from tests.conftest import signup_clinic


async def test_signup_clinic_creates_admin_and_returns_token(client: AsyncClient):
    ctx = await signup_clinic(client)
    me = await client.get("/api/v1/auth/me", headers=ctx["headers"])
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == ctx["email"]
    assert body["role"] == "SUPER_ADMIN"


async def test_signup_duplicate_email_conflicts(client: AsyncClient):
    ctx = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/auth/signup-clinic",
        json={
            "clinic_name": "Another Clinic",
            "admin_email": ctx["email"],
            "admin_password": "supersecret1",
            "admin_full_name": "Dr. Dupe",
        },
    )
    assert resp.status_code == 409


async def test_login_wrong_password_rejected(client: AsyncClient):
    ctx = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": ctx["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_correct_password_returns_token(client: AsyncClient):
    ctx = await signup_clinic(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": ctx["email"], "password": "supersecret1"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_me_requires_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
