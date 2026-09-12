"""Import every model here so SQLAlchemy's mapper registry sees all of them
(needed for relationship string resolution and Alembic autogenerate)."""
from app.models.agent_common import AgentType, ContactChannel
from app.models.agent_decision_rule import AgentDecisionRule
from app.models.agent_knowledge_document import AgentKnowledgeDocument
from app.models.announcement import Announcement
from app.models.announcement_acknowledgment import AnnouncementAcknowledgment
from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.clinic import Clinic
from app.models.clinic_document import ClinicDocument, ClinicDocumentType
from app.models.clinical_note import ClinicalNote, EntityType, NoteEntity, NoteStatus
from app.models.daily_recap import DailyRecap
from app.models.encounter import AudioFile, Encounter, EncounterStatus
from app.models.inbound_agent_config import InboundAgentConfig, PickupMode, SummaryShareWith
from app.models.inbound_call_session import CallOutcome, InboundCallSession
from app.models.outbound_agent_config import OutboundAgentConfig
from app.models.outbound_message_log import OutboundMessageLog, OutboundMessageStatus, OutboundMessageType
from app.models.patient import Patient
from app.models.patient_share_log import PatientShareLog
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate, TemplateType
from app.models.template_section_translation import TemplateSectionTranslation
from app.models.transcript import Transcript, TranscriptEntity
from app.models.user import ProviderAssistant, User, UserRole

__all__ = [
    "Base",
    "AgentType",
    "ContactChannel",
    "AgentDecisionRule",
    "AgentKnowledgeDocument",
    "Announcement",
    "AnnouncementAcknowledgment",
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
    "DailyRecap",
    "Encounter",
    "AudioFile",
    "EncounterStatus",
    "InboundAgentConfig",
    "PickupMode",
    "SummaryShareWith",
    "InboundCallSession",
    "CallOutcome",
    "OutboundAgentConfig",
    "OutboundMessageLog",
    "OutboundMessageStatus",
    "OutboundMessageType",
    "Patient",
    "PatientShareLog",
    "DoctorPreference",
    "NoteTemplate",
    "TemplateType",
    "TemplateSectionTranslation",
    "Transcript",
    "TranscriptEntity",
    "User",
    "UserRole",
    "ProviderAssistant",
]
