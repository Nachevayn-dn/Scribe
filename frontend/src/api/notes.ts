import { api } from "./client";
import type { AskAIResult, ClinicalNote, ShareResult, Transcript } from "../types";

export function getTranscript(encounterId: string) {
  return api.get<Transcript>(`/encounters/${encounterId}/transcript`);
}

export function editTranscriptLine(encounterId: string, lineIndex: number, newText: string) {
  return api.patch<Transcript>(`/encounters/${encounterId}/transcript`, {
    line_index: lineIndex,
    new_text: newText,
  });
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

/** Replaces the note's entire rendered_content — used to apply an Ask AI
 * revision, distinct from editNoteLine's single-line edits. */
export function replaceNoteContent(encounterId: string, renderedContent: string) {
  return api.patch<ClinicalNote>(`/encounters/${encounterId}/note`, {
    rendered_content: renderedContent,
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

/** Emails the transcript or note to whoever needs it (staff, EHR team,
 * the doctor themself). recipients may be empty if includeSelf is true. */
export function shareEncounterContent(
  encounterId: string,
  contentType: "transcript" | "note",
  recipients: string[],
  includeSelf: boolean,
) {
  return api.post<ShareResult>(`/encounters/${encounterId}/share`, {
    content_type: contentType,
    recipients,
    include_self: includeSelf,
  });
}

/** Free-form instruction against the current note — Claude either reworks
 * it (returns revised_content for the doctor to apply) or answers/looks
 * something up (returns answer + sources, informational only). */
export function askAI(encounterId: string, instruction: string) {
  return api.post<AskAIResult>(`/encounters/${encounterId}/note/ask-ai`, { instruction });
}
