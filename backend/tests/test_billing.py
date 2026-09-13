"""Billing: SUPER_ADMIN-only gating and a clean error when Stripe isn't
configured — same convention as test_telephony.py, since the test
environment has no real STRIPE_SECRET_KEY set and we never call the real
Stripe API in this suite."""
from httpx import AsyncClient

from tests.conftest import create_user, signup_clinic


async def test_non_admin_cannot_access_billing(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.get("/api/v1/billing/payment-method", headers=provider["headers"])
    assert resp.status_code == 403


async def test_setup_intent_without_stripe_configured_is_clean_400(client: AsyncClient):
    admin = await signup_clinic(client)

    resp = await client.post("/api/v1/billing/setup-intent", headers=admin["headers"])
    assert resp.status_code == 400
    assert "Stripe" in resp.json()["detail"] or "Billing" in resp.json()["detail"]


async def test_attach_payment_method_without_stripe_configured_is_clean_400(client: AsyncClient):
    admin = await signup_clinic(client)

    resp = await client.post(
        "/api/v1/billing/payment-method", headers=admin["headers"], json={"payment_method_id": "pm_fake"}
    )
    assert resp.status_code == 400


async def test_get_payment_method_with_no_customer_yet_is_none(client: AsyncClient):
    """Before any billing setup has happened (no Stripe customer created
    yet for this clinic), the payment-method check should short-circuit
    to "none on file" rather than trying to contact Stripe at all."""
    admin = await signup_clinic(client)

    resp = await client.get("/api/v1/billing/payment-method", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "has_payment_method": False,
        "brand": None,
        "last4": None,
        "exp_month": None,
        "exp_year": None,
    }


async def test_remove_payment_method_with_no_customer_yet_is_a_noop(client: AsyncClient):
    admin = await signup_clinic(client)

    resp = await client.delete("/api/v1/billing/payment-method", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["has_payment_method"] is False
