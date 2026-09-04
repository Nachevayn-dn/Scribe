export type UserRole = "SUPER_ADMIN" | "PROVIDER" | "ASSISTANT";
export type ThemePreference = "midnight" | "jade";

export interface CurrentUser {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  photo_url: string | null;
  theme_preference: ThemePreference;
  notification_email: string | null;
  language_preference: string | null;
  is_platform_admin: boolean;
}

export interface Clinic {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  is_active: boolean;
  contact_email: string | null;
  staff_email: string | null;
}

export interface User {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  license_number: string | null;
  photo_url: string | null;
  theme_preference: ThemePreference;
  notification_email: string | null;
  language_preference: string | null;
  is_platform_admin: boolean;
  // Null means credentials haven't been generated for this account yet.
  password_set_at: string | null;
}

export type ClinicDocumentType = "CONTRACT" | "ORDER_FORM" | "CONSENT_FORM";

export interface ClinicDocument {
  id: string;
  clinic_id: string;
  doc_type: ClinicDocumentType;
  original_filename: string;
  mime_type: string;
  uploaded_by_id: string;
  created_at: string;
}

export interface PlatformAnalytics {
  clinics_count: number;
  active_doctors_count: number;
  sessions_this_week: number;
  notes_signed_this_week: number;
}

export interface Patient {
  id: string;
  clinic_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  mrn: string | null;
  phone: string | null;
  email: string | null;
}

export type EncounterStatus =
  | "IN_PROGRESS"
  | "TRANSCRIBING"
  | "TRANSCRIPT_READY"
  | "EXTRACTING"
  | "NOTE_READY"
  | "SIGNED"
  | "FAILED";

export interface Encounter {
  id: string;
  clinic_id: string;
  patient_id: string;
  provider_id: string;
  created_by_id: string;
  status: EncounterStatus;
  failure_reason: string | null;
  // ISO-639-1 code chosen by the provider when starting the encounter
  // (see data/languages.ts) — null means auto-detect.
  language: string | null;
  is_scheduled_appointment: boolean;
  appointment_time: string | null;
  started_at: string;
  ended_at: string | null;
}

export interface DashboardSummary {
  sessions_this_week: number;
  scheduled_appointment_sessions_this_week: number;
  upcoming_appointments: number;
}

export type AppointmentStatus = "SCHEDULED" | "CANCELLED";

export interface Appointment {
  id: string;
  clinic_id: string;
  patient_id: string;
  provider_id: string;
  created_by_id: string;
  // The session this follow-up was scheduled from, if any.
  source_encounter_id: string | null;
  scheduled_time: string;
  reason: string | null;
  status: AppointmentStatus;
  created_at: string;
}

export type EntityType = "MEDICATION" | "PROCEDURE" | "DIAGNOSTIC" | "SYMPTOM" | "ALLERGY";

export interface NoteEntity {
  id: string;
  entity_type: EntityType;
  text: string;
  line_index: number;
  start_offset: number | null;
  end_offset: number | null;
  confidence: number | null;
  is_edited: boolean;
}

export type NoteStatus = "DRAFT" | "SIGNED";

export interface ClinicalNote {
  id: string;
  encounter_id: string;
  template_id: string | null;
  status: NoteStatus;
  signed_by_id: string | null;
  signed_at: string | null;
  rendered_content: string;
  entities: NoteEntity[];
}

export interface Transcript {
  id: string;
  encounter_id: string;
  raw_text: string;
  provider: string;
  language: string | null;
  created_at: string;
  // Same shape as ClinicalNote's, tagged lazily on first view of the
  // transcript (see backend/app/services/transcript_tagging.py).
  entities: NoteEntity[];
}

export type TemplateType = "CLINICAL_SUMMARY" | "REFERRAL_LETTER" | "CUSTOM";

export interface NoteTemplate {
  id: string;
  clinic_id: string | null;
  created_by_id: string | null;
  name: string;
  template_type: TemplateType;
  structure: string[];
  is_active: boolean;
}

export interface DoctorPreference {
  id: string;
  provider_id: string;
  trigger_phrase: string;
  instruction: string;
  is_active: boolean;
}

export interface ShareResult {
  status: "sent";
  message_id: string;
  recipients: string[];
}

export interface AskAISource {
  title: string;
  url: string;
}

export interface AskAIResult {
  result_type: "revision" | "answer";
  revised_content: string | null;
  answer: string | null;
  sources: AskAISource[];
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  audit_metadata: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
