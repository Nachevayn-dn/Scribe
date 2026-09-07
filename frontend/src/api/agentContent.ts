import { ApiError, api, getToken } from "./client";
import type { AgentDecisionRule, AgentKnowledgeDocument, AgentType } from "../types";

export function listKnowledgeDocuments(clinicId: string, agentType?: AgentType) {
  return api.get<AgentKnowledgeDocument[]>(`/platform/clinics/${clinicId}/knowledge-documents`, {
    agent_type: agentType,
  });
}

export function uploadKnowledgeDocument(clinicId: string, agentType: AgentType, title: string, file: File) {
  const form = new FormData();
  form.append("agent_type", agentType);
  form.append("title", title);
  form.append("file", file);
  return api.postForm<AgentKnowledgeDocument>(`/platform/clinics/${clinicId}/knowledge-documents`, form);
}

export async function downloadKnowledgeDocument(clinicId: string, documentId: string, filename: string) {
  const token = getToken();
  const res = await fetch(`/api/v1/platform/clinics/${clinicId}/knowledge-documents/${documentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to download document");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function retireKnowledgeDocument(clinicId: string, documentId: string) {
  return api.del<void>(`/platform/clinics/${clinicId}/knowledge-documents/${documentId}`);
}

export function listDecisionRules(clinicId: string, providerId?: string) {
  return api.get<AgentDecisionRule[]>(`/platform/clinics/${clinicId}/decision-rules`, {
    provider_id: providerId,
  });
}

export function createDecisionRule(
  clinicId: string,
  payload: { condition: string; action: string; priority?: number; provider_id?: string },
) {
  return api.post<AgentDecisionRule>(`/platform/clinics/${clinicId}/decision-rules`, payload);
}

export function updateDecisionRule(
  clinicId: string,
  ruleId: string,
  payload: Partial<Pick<AgentDecisionRule, "condition" | "action" | "priority" | "is_active" | "provider_id">>,
) {
  return api.patch<AgentDecisionRule>(`/platform/clinics/${clinicId}/decision-rules/${ruleId}`, payload);
}

export function deleteDecisionRule(clinicId: string, ruleId: string) {
  return api.del<void>(`/platform/clinics/${clinicId}/decision-rules/${ruleId}`);
}
