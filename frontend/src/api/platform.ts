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

export function updateClinic(
  clinicId: string,
  payload: Partial<Pick<Clinic, "name" | "address" | "phone" | "contact_email" | "staff_email" | "is_active">>,
) {
  return api.patch<Clinic>(`/platform/clinics/${clinicId}`, payload);
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

/** The preferred way to get a team member logged in: emails them a link
 * where they pick their own password, instead of an admin generating and
 * relaying a temp one (generateCredentials above, kept for fallback use). */
export function sendSetupLink(userId: string, sendEmail: boolean) {
  return api.post<{ setup_url: string; emailed: boolean; email_error: string | null }>(
    `/platform/users/${userId}/send-setup-link`,
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

export function uploadClinicDocument(
  clinicId: string,
  docType: ClinicDocumentType,
  file: File,
  providerId?: string,
) {
  const form = new FormData();
  form.append("doc_type", docType);
  if (providerId) form.append("provider_id", providerId);
  form.append("file", file);
  return api.postForm<ClinicDocument>(`/platform/clinics/${clinicId}/documents`, form);
}

/** Flips a doctor's data-retention override. The backend refuses to turn it
 * on unless a signed CONSENT_FORM document is already on file for them —
 * surface that ApiError message to the admin rather than retrying. */
export function updateRetention(userId: string, retainAllSessions: boolean) {
  return api.patch<User>(`/platform/users/${userId}/retention`, { retain_all_sessions: retainAllSessions });
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
