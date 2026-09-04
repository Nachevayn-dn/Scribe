import { api } from "./client";
import type { Appointment, AppointmentStatus } from "../types";

export function listAppointments(filters?: { patient_id?: string; upcoming_only?: boolean }) {
  return api.get<Appointment[]>("/appointments", {
    patient_id: filters?.patient_id,
    upcoming_only: filters?.upcoming_only ? "true" : undefined,
  });
}

export function scheduleAppointment(payload: {
  patient_id: string;
  provider_id: string;
  scheduled_time: string;
  reason?: string;
  source_encounter_id?: string;
}) {
  return api.post<Appointment>("/appointments", payload);
}

export function updateAppointment(
  id: string,
  payload: { scheduled_time?: string; reason?: string; status?: AppointmentStatus },
) {
  return api.patch<Appointment>(`/appointments/${id}`, payload);
}
