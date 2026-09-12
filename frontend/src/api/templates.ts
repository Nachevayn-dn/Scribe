import { api } from "./client";
import type { NoteTemplate, TemplateSectionTranslationDraft, TemplateType } from "../types";

export function listTemplates() {
  return api.get<NoteTemplate[]>("/templates");
}

export function createTemplate(payload: { name: string; template_type: TemplateType; structure: string[] }) {
  return api.post<NoteTemplate>("/templates", payload);
}

export function updateTemplate(
  templateId: string,
  payload: Partial<{ name: string; structure: string[]; is_active: boolean }>,
) {
  return api.patch<NoteTemplate>(`/templates/${templateId}`, payload);
}

export function deleteTemplate(templateId: string) {
  return api.del<void>(`/templates/${templateId}`);
}

/** Confirmed translation on file, or (is_confirmed: false) a fresh
 * Claude-drafted starting point the doctor can edit before saving. */
export function getTemplateTranslation(templateId: string, language: string) {
  return api.get<TemplateSectionTranslationDraft>(`/templates/${templateId}/translations/${language}`);
}

/** Saves the doctor's reviewed section titles — every future session in
 * this language with this template uses them automatically from here on. */
export function confirmTemplateTranslation(templateId: string, language: string, translatedStructure: string[]) {
  return api.put(`/templates/${templateId}/translations/${language}`, {
    translated_structure: translatedStructure,
  });
}
