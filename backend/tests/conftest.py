"""Shared pytest fixtures: an isolated Postgres test DB per test, an async
HTTP client bound to the FastAPI app, and helpers to sign up clinics/users."""
import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.template import NoteTemplate, TemplateType

settings = get_settings()

# Use a dedicated test database (created by the test runner / CI setup step),
# distinct from the dev database, so tests never touch real data.
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/scribe_test"

test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Mirrors alembic/versions/..._seed_global_templates.py — create_all()
    # builds schema only, not migration data, so tests that rely on the
    # default (no template_id) extraction path need these too.
    async with TestSessionLocal() as session:
        session.add_all(
            [
                NoteTemplate(
                    clinic_id=None,
                    name="Clinical Summary",
                    template_type=TemplateType.CLINICAL_SUMMARY,
                    structure=["Intake", "Diagnostics", "Next Steps", "Close"],
                ),
                NoteTemplate(
                    clinic_id=None,
                    name="Referral Letter",
                    template_type=TemplateType.REFERRAL_LETTER,
                    structure=["Reason for Referral", "Clinical History", "Findings", "Recommendation"],
                ),
            ]
        )
        await session.commit()

    yield
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # The audio-upload BackgroundTask (services.pipeline) doesn't go through
    # FastAPI's dependency injection, so it'd otherwise open a session
    # against the real dev database via its module-level AsyncSessionLocal.
    # Point it at the test DB for the duration of the test.
    import app.services.pipeline as pipeline_module

    original_session_local = pipeline_module.AsyncSessionLocal
    pipeline_module.AsyncSessionLocal = TestSessionLocal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    pipeline_module.AsyncSessionLocal = original_session_local
    app.dependency_overrides.clear()


async def signup_clinic(client: AsyncClient, *, clinic_name: str | None = None) -> dict:
    """Signs up a fresh clinic + SUPER_ADMIN and returns {token, headers, email}."""
    suffix = uuid.uuid4().hex[:8]
    email = f"admin-{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/signup-clinic",
        json={
            "clinic_name": clinic_name or f"Test Clinic {suffix}",
            "admin_email": email,
            "admin_password": "supersecret1",
            "admin_full_name": "Dr. Admin",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}, "email": email}


async def create_user(
    client: AsyncClient, admin_headers: dict, *, role: str, email: str | None = None
) -> dict:
    suffix = uuid.uuid4().hex[:8]
    email = email or f"user-{suffix}@example.com"
    resp = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "password": "supersecret1",
            "full_name": f"Test {role.title()}",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {**body, "token": token, "headers": {"Authorization": f"Bearer {token}"}}
