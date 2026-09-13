from pydantic import BaseModel, Field


class SetupIntentResponse(BaseModel):
    """Everything the frontend needs to collect a card with Stripe.js: the
    publishable key (safe to expose — it's not a secret) and the client
    secret for this specific SetupIntent."""

    client_secret: str
    publishable_key: str


class PaymentMethodResponse(BaseModel):
    has_payment_method: bool
    brand: str | None = None
    last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None

    @classmethod
    def from_summary(cls, summary: dict | None) -> "PaymentMethodResponse":
        if summary is None:
            return cls(has_payment_method=False)
        return cls(has_payment_method=True, **summary)


class AttachPaymentMethodRequest(BaseModel):
    payment_method_id: str = Field(min_length=1)
