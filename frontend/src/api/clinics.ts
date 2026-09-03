import { api } from "./client";
import type { Clinic } from "../types";

export function getMyClinic() {
  return api.get<Clinic>("/clinics/me");
}

export function updateMyClinic(payload: Partial<Pick<Clinic, "name" | "address" | "phone" | "contact_email" | "staff_email">>) {
  return api.patch<Clinic>("/clinics/me", payload);
}
