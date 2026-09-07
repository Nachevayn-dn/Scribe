import { api } from "./client";
import type { CallSession } from "../types";

export function listCalls() {
  return api.get<CallSession[]>("/calls");
}

export function getCall(id: string) {
  return api.get<CallSession>(`/calls/${id}`);
}

export function approveAppointment(callId: string) {
  return api.post<CallSession>(`/calls/${callId}/approve-appointment`);
}
