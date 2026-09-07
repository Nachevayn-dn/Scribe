"""add inbound/outbound agent tables (config, knowledge docs, decision rules, call sessions, message log)

Revision ID: 0010_add_inbound_outbound_agents
Revises: 0009_add_platform_admin
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010_add_inbound_outbound_agents"
down_revision: Union[str, None] = "0009_add_platform_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- appointments: PROPOSED status + reminder idempotency stamps ---
    op.execute("ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'PROPOSED'")
    op.add_column("appointments", sa.Column("reminder_day_before_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("appointments", sa.Column("reminder_hours_before_sent_at", sa.DateTime(timezone=True), nullable=True))

    # --- inbound_agent_configs ---
    op.create_table(
        "inbound_agent_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("phone_number_sid", sa.String(64), nullable=True),
        sa.Column("whatsapp_number", sa.String(30), nullable=True),
        sa.Column("default_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("additional_languages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "greeting_text",
            sa.String(1000),
            nullable=False,
            server_default="Thank you for calling. How can I help you today?",
        ),
        sa.Column(
            "pickup_mode",
            sa.Enum("ALWAYS", "AFTER_HOURS", "NO_ANSWER", name="agent_pickup_mode"),
            nullable=False,
            server_default="ALWAYS",
        ),
        sa.Column("after_hours_start", sa.Time(), nullable=True),
        sa.Column("after_hours_end", sa.Time(), nullable=True),
        sa.Column("no_answer_timeout_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("forward_to_number", sa.String(20), nullable=True),
        sa.Column("recording_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "share_summary_with",
            sa.Enum("DOCTOR_ONLY", "TEAM", name="summary_share_with"),
            nullable=False,
            server_default="DOCTOR_ONLY",
        ),
        sa.Column(
            "share_channel",
            sa.Enum("EMAIL", "SMS", "WHATSAPP", name="agent_share_channel"),
            nullable=False,
            server_default="EMAIL",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # --- outbound_agent_configs ---
    op.create_table(
        "outbound_agent_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("day_before_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("day_before_send_hour", sa.Time(), nullable=False, server_default="10:00:00"),
        sa.Column("hours_before_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("hours_before_offset", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("default_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("additional_languages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # --- agent_knowledge_documents ---
    op.create_table(
        "agent_knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("agent_type", sa.Enum("INBOUND", "OUTBOUND", name="agent_type"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_knowledge_documents_clinic_id", "agent_knowledge_documents", ["clinic_id"])

    # --- agent_decision_rules ---
    op.create_table(
        "agent_decision_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition", sa.String(1000), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_decision_rules_clinic_id", "agent_decision_rules", ["clinic_id"])

    # --- inbound_call_sessions ---
    op.create_table(
        "inbound_call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("twilio_call_sid", sa.String(64), nullable=False, unique=True),
        sa.Column("from_number", sa.String(20), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("recording_sid", sa.String(64), nullable=True),
        sa.Column("recording_url", sa.String(1000), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum(
                "IN_PROGRESS", "APPOINTMENT_PROPOSED", "INFO_ONLY", "EMERGENCY_ESCALATED", "ABANDONED",
                name="call_outcome",
            ),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column("proposed_appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column(
            "preferred_contact_channel",
            sa.Enum("EMAIL", "SMS", "WHATSAPP", name="call_contact_channel"),
            nullable=True,
        ),
        sa.Column("language_used", sa.String(10), nullable=True),
        sa.Column("summary_shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_inbound_call_sessions_clinic_id", "inbound_call_sessions", ["clinic_id"])
    op.create_index("ix_inbound_call_sessions_twilio_call_sid", "inbound_call_sessions", ["twilio_call_sid"])

    # --- outbound_message_logs ---
    op.create_table(
        "outbound_message_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("channel", sa.Enum("EMAIL", "SMS", "WHATSAPP", name="message_channel"), nullable=False),
        sa.Column(
            "message_type",
            sa.Enum(
                "APPOINTMENT_CONFIRMATION", "REMINDER_DAY_BEFORE", "REMINDER_HOURS_BEFORE",
                name="outbound_message_type",
            ),
            nullable=False,
        ),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("SENT", "FAILED", name="outbound_message_status"),
            nullable=False,
            server_default="SENT",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_outbound_message_logs_clinic_id", "outbound_message_logs", ["clinic_id"])


def downgrade() -> None:
    op.drop_index("ix_outbound_message_logs_clinic_id", table_name="outbound_message_logs")
    op.drop_table("outbound_message_logs")
    op.execute("DROP TYPE IF EXISTS outbound_message_status")
    op.execute("DROP TYPE IF EXISTS outbound_message_type")
    op.execute("DROP TYPE IF EXISTS message_channel")

    op.drop_index("ix_inbound_call_sessions_twilio_call_sid", table_name="inbound_call_sessions")
    op.drop_index("ix_inbound_call_sessions_clinic_id", table_name="inbound_call_sessions")
    op.drop_table("inbound_call_sessions")
    op.execute("DROP TYPE IF EXISTS call_contact_channel")
    op.execute("DROP TYPE IF EXISTS call_outcome")

    op.drop_index("ix_agent_decision_rules_clinic_id", table_name="agent_decision_rules")
    op.drop_table("agent_decision_rules")

    op.drop_index("ix_agent_knowledge_documents_clinic_id", table_name="agent_knowledge_documents")
    op.drop_table("agent_knowledge_documents")
    op.execute("DROP TYPE IF EXISTS agent_type")

    op.drop_table("outbound_agent_configs")

    op.drop_table("inbound_agent_configs")
    op.execute("DROP TYPE IF EXISTS agent_share_channel")
    op.execute("DROP TYPE IF EXISTS summary_share_with")
    op.execute("DROP TYPE IF EXISTS agent_pickup_mode")

    op.drop_column("appointments", "reminder_hours_before_sent_at")
    op.drop_column("appointments", "reminder_day_before_sent_at")
    # Postgres can't drop a single enum value — downgrading past PROPOSED
    # would need a full type rebuild; left as a known limitation, matching
    # how other additive enum migrations in this repo handle downgrade.
