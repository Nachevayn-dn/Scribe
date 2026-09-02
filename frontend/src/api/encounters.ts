import { api } from "./client";
import type { Encounter } from "../types";

export function listEncounters(filters?: { patient_id?: string; provider_id?: string }) {
  return api.get<Encounter[]>("/encounters", filters);
}

export function startEncounter(patientId: string, providerId: string) {
  return api.post<Encounter>("/encounters", { patient_id: patientId, provider_id: providerId });
}

export function getEncounter(id: string) {
  return api.get<Encounter>(`/encounters/${id}`);
}

export function endEncounter(id: string) {
  return api.patch<Encounter>(`/encounters/${id}`, {});
}

export function uploadAudio(encounterId: string, file: Blob, filename: string) {
  const form = new FormData();
  form.append("file", file, filename);
  return api.postForm<Encounter>(`/encounters/${encounterId}/audio`, form);
}
