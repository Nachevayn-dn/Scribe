import { api } from "./client";
import type { PaymentMethodInfo } from "../types";

export function createSetupIntent() {
  return api.post<{ client_secret: string; publishable_key: string }>("/billing/setup-intent");
}

export function getPaymentMethod() {
  return api.get<PaymentMethodInfo>("/billing/payment-method");
}

export function attachPaymentMethod(paymentMethodId: string) {
  return api.post<PaymentMethodInfo>("/billing/payment-method", { payment_method_id: paymentMethodId });
}

export function removePaymentMethod() {
  return api.del<PaymentMethodInfo>("/billing/payment-method");
}
