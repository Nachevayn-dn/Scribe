import { api } from "./client";
import type { InboundAgentConfig } from "../types";

export function getTelephonyConfig(clinicId: string) {
  return api.get<InboundAgentConfig>(`/platform/clinics/${clinicId}/telephony`);
}

export function updateTelephonyConfig(clinicId: string, payload: Partial<InboundAgentConfig>) {
  return api.patch<InboundAgentConfig>(`/platform/clinics/${clinicId}/telephony`, payload);
}

export function provisionPhoneNumber(clinicId: string) {
  return api.post<{ phone_number: string; phone_number_sid: string; webhook_configured: boolean }>(
    `/platform/clinics/${clinicId}/telephony/provision-number`,
  );
}

export function connectWhatsApp(clinicId: string, whatsappNumber?: string) {
  return api.post<InboundAgentConfig>(`/platform/clinics/${clinicId}/telephony/whatsapp/connect`, {
    whatsapp_number: whatsappNumber || undefined,
  });
}
