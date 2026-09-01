export type UserRole = "SUPER_ADMIN" | "PROVIDER" | "ASSISTANT";

export interface CurrentUser {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface Clinic {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  is_active: boolean;
}

export interface User {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  license_number: string | null;
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
  started_at: string;
  ended_at: string | null;
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
