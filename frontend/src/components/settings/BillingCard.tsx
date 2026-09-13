import { useEffect, useState } from "react";
import { loadStripe, type Stripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import * as billingApi from "../../api/billing";
import { ApiError } from "../../api/client";
import type { PaymentMethodInfo } from "../../types";

// loadStripe() must only ever be called once per publishable key — calling
// it again on every render leaks connections. Cached at module scope,
// keyed by key, since the key itself never changes within a session.
const stripePromiseByKey = new Map<string, Promise<Stripe | null>>();
function getStripePromise(publishableKey: string): Promise<Stripe | null> {
  let cached = stripePromiseByKey.get(publishableKey);
  if (!cached) {
    cached = loadStripe(publishableKey);
    stripePromiseByKey.set(publishableKey, cached);
  }
  return cached;
}

const BRAND_LABELS: Record<string, string> = {
  visa: "Visa",
  mastercard: "Mastercard",
  amex: "American Express",
  discover: "Discover",
  diners: "Diners Club",
  jcb: "JCB",
  unionpay: "UnionPay",
};

/** The "Payment details" section of Settings — SUPER_ADMIN only (the
 * backend enforces this too). Shows the clinic's saved card (brand/last4
 * only — we never see or store the full number) with add/replace/remove,
 * via Stripe's own hosted card form (Stripe Elements) so a real card
 * number never passes through this app's own frontend code, let alone its
 * backend. */
export function BillingCard() {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethodInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [setup, setSetup] = useState<{ clientSecret: string; publishableKey: string } | null>(null);
  const [removing, setRemoving] = useState(false);

  async function refresh() {
    try {
      const pm = await billingApi.getPaymentMethod();
      setPaymentMethod(pm);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load billing info");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleStartAdding() {
    setError(null);
    setAdding(true);
    try {
      const intent = await billingApi.createSetupIntent();
      if (!intent.publishable_key) {
        setError(
          "Billing isn't set up yet — a platform admin needs to add a Stripe publishable key first.",
        );
        setAdding(false);
        return;
      }
      setSetup({ clientSecret: intent.client_secret, publishableKey: intent.publishable_key });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start card setup");
      setAdding(false);
    }
  }

  async function handleRemove() {
    if (!window.confirm("Remove the saved payment method?")) return;
    setRemoving(true);
    setError(null);
    try {
      const pm = await billingApi.removePaymentMethod();
      setPaymentMethod(pm);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove payment method");
    } finally {
      setRemoving(false);
    }
  }

  function handleCancelAdding() {
    setAdding(false);
    setSetup(null);
  }

  async function handleSaved(paymentMethodId: string) {
    try {
      const pm = await billingApi.attachPaymentMethod(paymentMethodId);
      setPaymentMethod(pm);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Card was confirmed but couldn't be saved");
    } finally {
      setAdding(false);
      setSetup(null);
    }
  }

  return (
    <div id="billing" className="card stack">
      <strong>Payment details</strong>
      <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
        Your clinic's saved card for MedicDesk.ai billing. Card numbers are entered directly with
        Stripe and never pass through our servers.
      </p>

      {error && <div className="error-text">{error}</div>}

      {loading ? (
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>Loading…</p>
      ) : setup ? (
        <Elements stripe={getStripePromise(setup.publishableKey)} options={{ clientSecret: setup.clientSecret }}>
          <CardSetupForm onSaved={handleSaved} onCancel={handleCancelAdding} />
        </Elements>
      ) : paymentMethod?.has_payment_method ? (
        <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
          <span style={{ fontSize: 14 }}>
            {BRAND_LABELS[paymentMethod.brand ?? ""] ?? paymentMethod.brand} ending in{" "}
            {paymentMethod.last4} — expires {paymentMethod.exp_month}/{paymentMethod.exp_year}
          </span>
          <div className="row">
            <button className="btn" onClick={handleStartAdding} disabled={adding}>
              Replace card
            </button>
            <button className="btn" onClick={handleRemove} disabled={removing}>
              {removing ? "Removing…" : "Remove"}
            </button>
          </div>
        </div>
      ) : (
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-primary" onClick={handleStartAdding} disabled={adding}>
            {adding ? "Loading…" : "Add payment method"}
          </button>
        </div>
      )}
    </div>
  );
}

function CardSetupForm({
  onSaved,
  onCancel,
}: {
  onSaved: (paymentMethodId: string) => void;
  onCancel: () => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setSubmitting(true);
    setFormError(null);
    const { error, setupIntent } = await stripe.confirmSetup({
      elements,
      redirect: "if_required",
    });
    if (error) {
      setFormError(error.message ?? "Failed to save card");
      setSubmitting(false);
      return;
    }
    const paymentMethodId =
      typeof setupIntent?.payment_method === "string"
        ? setupIntent.payment_method
        : setupIntent?.payment_method?.id;
    if (!paymentMethodId) {
      setFormError("Card setup didn't complete — please try again");
      setSubmitting(false);
      return;
    }
    onSaved(paymentMethodId);
  }

  return (
    <form className="stack" onSubmit={handleSubmit}>
      <PaymentElement />
      {formError && <div className="error-text">{formError}</div>}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={!stripe || submitting}>
          {submitting ? "Saving…" : "Save card"}
        </button>
      </div>
    </form>
  );
}
