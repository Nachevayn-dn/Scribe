"""Billing — a clinic's saved payment method, via Stripe.

Mirrors email_service.py/twilio_client.py's shape: a clean "not configured"
error instead of a crash when no API key is set, and Stripe's own
exceptions wrapped into clean RuntimeErrors rather than raw tracebacks
reaching the API layer.

We never see or store a raw card number. The frontend collects it directly
with Stripe.js (a SetupIntent confirmed client-side) and hands us back only
a payment_method id — an opaque Stripe reference — which we attach to the
clinic's Stripe Customer. The only things this backend ever persists are
Clinic.stripe_customer_id and whatever id Stripe assigns; card data itself
lives only in Stripe's own PCI-compliant systems.
"""
import logging

import stripe

from app.config import get_settings
from app.models.clinic import Clinic

settings = get_settings()
logger = logging.getLogger(__name__)


class StripeNotConfiguredError(RuntimeError):
    pass


def _require_configured() -> None:
    if not settings.stripe_secret_key:
        raise StripeNotConfiguredError(
            "Billing isn't set up yet — add a Stripe secret key under Settings > "
            "Payment details (platform admin)."
        )
    stripe.api_key = settings.stripe_secret_key


def ensure_customer(clinic: Clinic) -> str:
    """Returns the clinic's Stripe customer id, creating one on first use.
    Caller is responsible for committing the session afterward — this only
    mutates the passed-in ORM object."""
    _require_configured()
    if clinic.stripe_customer_id:
        return clinic.stripe_customer_id
    try:
        customer = stripe.Customer.create(
            name=clinic.name,
            email=clinic.contact_email or None,
            metadata={"clinic_id": str(clinic.id)},
        )
    except stripe.StripeError as exc:
        logger.exception("Stripe customer creation failed")
        raise RuntimeError(f"Failed to set up billing: {exc.user_message or exc}") from exc
    clinic.stripe_customer_id = customer.id
    return customer.id


def create_setup_intent(customer_id: str) -> stripe.SetupIntent:
    """A SetupIntent lets the frontend collect and validate a card via
    Stripe.js without charging anything — confirming it client-side is what
    actually tokenizes the card, never touching this backend."""
    _require_configured()
    try:
        return stripe.SetupIntent.create(customer=customer_id, usage="off_session")
    except stripe.StripeError as exc:
        logger.exception("Stripe SetupIntent creation failed")
        raise RuntimeError(f"Failed to start card setup: {exc.user_message or exc}") from exc


def get_payment_method_summary(customer_id: str) -> dict | None:
    """Returns {brand, last4, exp_month, exp_year} for the customer's
    default payment method, or None if none is set. Never returns anything
    resembling a full card number — Stripe itself never gives us one."""
    _require_configured()
    try:
        customer = stripe.Customer.retrieve(customer_id, expand=["invoice_settings.default_payment_method"])
    except stripe.StripeError as exc:
        logger.exception("Stripe customer lookup failed")
        raise RuntimeError(f"Failed to look up billing info: {exc.user_message or exc}") from exc
    pm = customer.invoice_settings.default_payment_method if customer.invoice_settings else None
    if not pm or not getattr(pm, "card", None):
        return None
    return {
        "brand": pm.card.brand,
        "last4": pm.card.last4,
        "exp_month": pm.card.exp_month,
        "exp_year": pm.card.exp_year,
    }


def attach_payment_method(customer_id: str, payment_method_id: str) -> dict:
    """Attaches an already-tokenized payment method (from a confirmed
    SetupIntent) to the customer and makes it the default for future
    charges. Returns the same summary shape as get_payment_method_summary."""
    _require_configured()
    try:
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        stripe.Customer.modify(
            customer_id, invoice_settings={"default_payment_method": payment_method_id}
        )
    except stripe.StripeError as exc:
        logger.exception("Stripe payment method attach failed")
        raise RuntimeError(f"Failed to save payment method: {exc.user_message or exc}") from exc
    summary = get_payment_method_summary(customer_id)
    if summary is None:
        raise RuntimeError("Payment method was attached but could not be confirmed — please try again.")
    return summary


def remove_payment_method(customer_id: str) -> None:
    _require_configured()
    try:
        customer = stripe.Customer.retrieve(customer_id, expand=["invoice_settings.default_payment_method"])
        pm = customer.invoice_settings.default_payment_method if customer.invoice_settings else None
        if pm:
            stripe.PaymentMethod.detach(pm.id)
    except stripe.StripeError as exc:
        logger.exception("Stripe payment method removal failed")
        raise RuntimeError(f"Failed to remove payment method: {exc.user_message or exc}") from exc
