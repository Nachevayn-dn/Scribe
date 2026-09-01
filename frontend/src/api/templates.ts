import { api } from "./client";
import type { NoteTemplate, TemplateType } from "../types";

export function listTemplates() {
  return api.get<NoteTemplate[]>("/templates");
}

export function createTemplate(payload: { name: string; template_type: TemplateType; structure: string[] }) {
  return api.post<NoteTemplate>("/templates", payload);
}
