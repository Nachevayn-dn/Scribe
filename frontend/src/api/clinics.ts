import { api } from "./client";
import type { Clinic } from "../types";

export function getMyClinic() {
  return api.get<Clinic>("/clinics/me");
}

export function updateMyClinic(payload: Partial<Pick<Clinic, "name" | "address" | "phone" | "contact_email" | "staff_email">>) {
  return api.patch<Clinic>("/clinics/me", payload);
}

export function getMyClinicGreeting() {
  return api.get<{ greeting_text: string }>("/clinics/me/greeting");
}

export function updateMyClinicGreeting(greetingText: string) {
  return api.patch<{ greeting_text: string }>("/clinics/me/greeting", { greeting_text: greetingText });
}
