"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # Each Enum is created lazily (checkfirst) the first time it's used as a
    # column type below, so no explicit CREATE TYPE step is needed here.
    user_role = postgresql.ENUM(
        "SUPER_ADMIN", "PROVIDER", "ASSISTANT", name="user_role", create_type=False
    )
    encounter_status = postgresql.ENUM(
        "IN_PROGRESS", "TRANSCRIBING", "EXTRACTING", "NOTE_READY", "SIGNED", "FAILED",
        name="encounter_status", create_type=False,
    )
    note_status = postgresql.ENUM("DRAFT", "SIGNED", name="note_status", create_type=False)
    entity_type = postgresql.ENUM(
        "MEDICATION", "PROCEDURE", "DIAGNOSTIC", "SYMPTOM", "ALLERGY",
        name="entity_type", create_type=False,
    )
    template_type = postgresql.ENUM(
        "CLINICAL_SUMMARY", "REFERRAL_LETTER", "CUSTOM", name="template_type", create_type=False
    )
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    encounter_status.create(bind, checkfirst=True)
    note_status.create(bind, checkfirst=True)
    entity_type.create(bind, checkfirst=True)
    template_type.create(bind, checkfirst=True)

    op.create_table(
        "clinics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("license_number", sa.String(100), nullable=True),
    )
    op.create_index("ix_users_clinic_id", "users", ["clinic_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "provider_assistants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assistant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("provider_id", "assistant_id", name="uq_provider_assistant"),
    )
    op.create_index("ix_provider_assistants_clinic_id", "provider_assistants", ["clinic_id"])
    op.create_index("ix_provider_assistants_provider_id", "provider_assistants", ["provider_id"])
    op.create_index("ix_provider_assistants_assistant_id", "provider_assistants", ["assistant_id"])

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=False),
        sa.Column("mrn", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])

    op.create_table(
        "note_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("template_type", template_type, nullable=False),
        sa.Column("structure", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_note_templates_clinic_id", "note_templates", ["clinic_id"])

    op.create_table(
        "encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", encounter_status, nullable=False, server_default="IN_PROGRESS"),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_encounters_clinic_id", "encounters", ["clinic_id"])
    op.create_index("ix_encounters_patient_id", "encounters", ["patient_id"])
    op.create_index("ix_encounters_provider_id", "encounters", ["provider_id"])

    op.create_table(
        "audio_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_audio_files_encounter_id", "audio_files", ["encounter_id"])

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("language", sa.String(20), nullable=True),
    )
    op.create_index("ix_transcripts_encounter_id", "transcripts", ["encounter_id"])

    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False, unique=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("note_templates.id"), nullable=True),
        sa.Column("status", note_status, nullable=False, server_default="DRAFT"),
        sa.Column("signed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rendered_content", sa.Text, nullable=False, server_default=""),
        sa.Column("raw_structured", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_clinical_notes_encounter_id", "clinical_notes", ["encounter_id"])

    op.create_table(
        "note_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinical_notes.id"), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column("line_index", sa.Integer, nullable=False),
        sa.Column("start_offset", sa.Integer, nullable=True),
        sa.Column("end_offset", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_note_entities_clinical_note_id", "note_entities", ["clinical_note_id"])

    op.create_table(
        "doctor_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger_phrase", sa.String(500), nullable=False),
        sa.Column("instruction", sa.String(1000), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_doctor_preferences_provider_id", "doctor_preferences", ["provider_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("audit_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_logs_clinic_id", "audit_logs", ["clinic_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("doctor_preferences")
    op.drop_table("note_entities")
    op.drop_table("clinical_notes")
    op.drop_table("transcripts")
    op.drop_table("audio_files")
    op.drop_table("encounters")
    op.drop_table("note_templates")
    op.drop_table("patients")
    op.drop_table("provider_assistants")
    op.drop_table("users")
    op.drop_table("clinics")

    bind = op.get_bind()
    for enum_name in ("template_type", "entity_type", "note_status", "encounter_status", "user_role"):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
