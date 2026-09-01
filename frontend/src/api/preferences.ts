import { api } from "./client";
import type { DoctorPreference } from "../types";

export function listPreferences(providerId?: string) {
  return api.get<DoctorPreference[]>("/preferences", { provider_id: providerId });
}

export function createPreference(payload: { trigger_phrase: string; instruction: string; provider_id?: string }) {
  return api.post<DoctorPreference>("/preferences", payload);
}

export function updatePreference(id: string, payload: Partial<Pick<DoctorPreference, "trigger_phrase" | "instruction" | "is_active">>) {
  return api.patch<DoctorPreference>(`/preferences/${id}`, payload);
}

export function deletePreference(id: string) {
  return api.del<void>(`/preferences/${id}`);
}
