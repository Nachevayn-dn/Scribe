import { api } from "./client";
import type { Patient } from "../types";

export function listPatients() {
  return api.get<Patient[]>("/patients");
}

export function createPatient(payload: {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  mrn?: string;
  phone?: string;
  email?: string;
}) {
  return api.post<Patient>("/patients", payload);
}

export function getPatient(id: string) {
  return api.get<Patient>(`/patients/${id}`);
}
