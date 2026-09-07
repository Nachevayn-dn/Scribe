import { api } from "./client";
import type { OutboundAgentConfig } from "../types";

export function getOutboundConfig(clinicId: string) {
  return api.get<OutboundAgentConfig>(`/platform/clinics/${clinicId}/outbound-config`);
}

export function updateOutboundConfig(clinicId: string, payload: Partial<OutboundAgentConfig>) {
  return api.patch<OutboundAgentConfig>(`/platform/clinics/${clinicId}/outbound-config`, payload);
}
