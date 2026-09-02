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

/** Doctor-initiated: generate (or regenerate, against a different template)
 * the clinical note from the encounter's transcript. Synchronous — a single
 * Claude call, fast enough to just await. */
export function generateNote(encounterId: string, templateId: string) {
  return api.post<ClinicalNote>(
    `/encounters/${encounterId}/note/generate`,
    undefined,
    { template_id: templateId },
  );
}
