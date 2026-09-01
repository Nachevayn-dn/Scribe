import { api } from "./client";
import type { ClinicalNote, Transcript } from "../types";

export function getTranscript(encounterId: string) {
  return api.get<Transcript>(`/encounters/${encounterId}/transcript`);
}

export function getNote(encounterId: string) {
  return api.get<ClinicalNote>(`/encounters/${encounterId}/note`);
}

export function editNoteLine(encounterId: string, lineIndex: number, newText: string) {
  return api.patch<ClinicalNote>(`/encounters/${encounterId}/note`, {
    line_index: lineIndex,
    new_text: newText,
  });
}

export function signNote(encounterId: string) {
  return api.post<ClinicalNote>(`/encounters/${encounterId}/note/sign`);
}

export function regenerateNote(encounterId: string, templateId?: string) {
  return api.post<{ status: string }>(
    `/encounters/${encounterId}/note/regenerate`,
    undefined,
    { template_id: templateId },
  );
}

export function renderNote(encounterId: string, templateId: string) {
  return api.post<ClinicalNote>(
    `/encounters/${encounterId}/note/render`,
    undefined,
    { template_id: templateId },
  );
}
