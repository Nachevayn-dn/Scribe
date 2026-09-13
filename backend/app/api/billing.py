"""A clinic's own billing/payment method — SUPER_ADMIN only, same gate as
the rest of a clinic's financial/contact settings (api/clinics.py). See
services/billing_service.py for what is and isn't stored here.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestError
from app.database import get_db
from app.deps import require_role
from app.models.user import User, UserRole
from app.schemas.billing import AttachPaymentMethodRequest, PaymentMethodResponse, SetupIntentResponse
from app.services import billing_service
from app.services.billing_service import StripeNotConfiguredError

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()


@router.post("/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SetupIntentResponse:
    clinic = current_user.clinic
    try:
        customer_id = billing_service.ensure_customer(clinic)
        await db.commit()
        intent = billing_service.create_setup_intent(customer_id)
    except StripeNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise BadRequestError(str(exc)) from exc
    return SetupIntentResponse(client_secret=intent.client_secret, publishable_key=settings.stripe_publishable_key or "")


@router.get("/payment-method", response_model=PaymentMethodResponse)
async def get_payment_method(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> PaymentMethodResponse:
    clinic = current_user.clinic
    if not clinic.stripe_customer_id:
        return PaymentMethodResponse(has_payment_method=False)
    try:
        summary = billing_service.get_payment_method_summary(clinic.stripe_customer_id)
    except StripeNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise BadRequestError(str(exc)) from exc
    return PaymentMethodResponse.from_summary(summary)


@router.post("/payment-method", response_model=PaymentMethodResponse)
async def attach_payment_method(
    payload: AttachPaymentMethodRequest,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PaymentMethodResponse:
    clinic = current_user.clinic
    try:
        customer_id = billing_service.ensure_customer(clinic)
        await db.commit()
        summary = billing_service.attach_payment_method(customer_id, payload.payment_method_id)
    except StripeNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise BadRequestError(str(exc)) from exc
    return PaymentMethodResponse.from_summary(summary)


@router.delete("/payment-method", response_model=PaymentMethodResponse)
async def remove_payment_method(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> PaymentMethodResponse:
    clinic = current_user.clinic
    if not clinic.stripe_customer_id:
        return PaymentMethodResponse(has_payment_method=False)
    try:
        billing_service.remove_payment_method(clinic.stripe_customer_id)
    except StripeNotConfiguredError as exc:
        raise BadRequestError(str(exc)) from exc
    except RuntimeError as exc:
        raise BadRequestError(str(exc)) from exc
    return PaymentMethodResponse(has_payment_method=False)
