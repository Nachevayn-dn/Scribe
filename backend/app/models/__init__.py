"""Import every model here so SQLAlchemy's mapper registry sees all of them
(needed for relationship string resolution and Alembic autogenerate)."""
from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.clinic import Clinic
from app.models.clinic_document import ClinicDocument, ClinicDocumentType
from app.models.clinical_note import ClinicalNote, EntityType, NoteEntity, NoteStatus
from app.models.encounter import AudioFile, Encounter, EncounterStatus
from app.models.patient import Patient
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate, TemplateType
from app.models.transcript import Transcript, TranscriptEntity
from app.models.user import ProviderAssistant, User, UserRole

__all__ = [
    "Base",
    "Appointment",
    "AppointmentStatus",
    "AuditLog",
    "Clinic",
    "ClinicDocument",
    "ClinicDocumentType",
    "ClinicalNote",
    "NoteEntity",
    "NoteStatus",
    "EntityType",
    "Encounter",
    "AudioFile",
    "EncounterStatus",
    "Patient",
    "DoctorPreference",
    "NoteTemplate",
    "TemplateType",
    "Transcript",
    "TranscriptEntity",
    "User",
    "UserRole",
    "ProviderAssistant",
]
