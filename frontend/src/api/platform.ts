import { ApiError, api, getToken } from "./client";
import type {
  Clinic,
  ClinicDocument,
  ClinicDocumentType,
  Encounter,
  Patient,
  PlatformAnalytics,
  User,
  UserRole,
} from "../types";

export function listClinics() {
  return api.get<Clinic[]>("/platform/clinics");
}

export function createClinic(payload: { name: string; address?: string; phone?: string }) {
  return api.post<Clinic>("/platform/clinics", payload);
}

export function listClinicDoctors(clinicId: string) {
  return api.get<User[]>(`/platform/clinics/${clinicId}/doctors`);
}

export function provisionDoctor(
  clinicId: string,
  payload: { email: string; full_name: string; role: Extract<UserRole, "PROVIDER" | "ASSISTANT">; license_number?: string },
) {
  return api.post<User>(`/platform/clinics/${clinicId}/doctors`, payload);
}

export function generateCredentials(userId: string, sendEmail: boolean) {
  return api.post<{ temp_password: string; emailed: boolean; email_error: string | null }>(
    `/platform/users/${userId}/generate-credentials`,
    undefined,
    { send_email: sendEmail ? "true" : "false" },
  );
}

export function listClinicPatients(clinicId: string) {
  return api.get<Patient[]>(`/platform/clinics/${clinicId}/patients`);
}

export function listClinicEncounters(clinicId: string) {
  return api.get<Encounter[]>(`/platform/clinics/${clinicId}/encounters`);
}

export function listClinicDocuments(clinicId: string) {
  return api.get<ClinicDocument[]>(`/platform/clinics/${clinicId}/documents`);
}

export function uploadClinicDocument(clinicId: string, docType: ClinicDocumentType, file: File) {
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  return api.postForm<ClinicDocument>(`/platform/clinics/${clinicId}/documents`, form);
}

/** The download endpoint requires the same bearer auth as every other API
 * call, so a plain <a href> won't work — fetch it with the token attached
 * and hand the browser a blob to save instead. */
export async function downloadClinicDocument(clinicId: string, documentId: string, filename: string) {
  const token = getToken();
  const res = await fetch(`/api/v1/platform/clinics/${clinicId}/documents/${documentId}/download`, {
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

export function getAnalytics() {
  return api.get<PlatformAnalytics>("/platform/analytics");
}
