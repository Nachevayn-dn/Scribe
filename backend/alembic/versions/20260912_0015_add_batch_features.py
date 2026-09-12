"""Batch feature set: daily dashboard recaps, per-template section-title
translations, a "share with patient" history, and platform-wide
announcements + acknowledgments.

Revision ID: 0015_add_batch_features
Revises: 0014_add_encounter_archived_at
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015_add_batch_features"
down_revision: Union[str, None] = "0014_add_encounter_archived_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_recaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recap_date", sa.Date(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "recap_date", name="uq_daily_recap_user_date"),
    )
    op.create_index("ix_daily_recaps_user_id", "daily_recaps", ["user_id"])

    op.create_table(
        "template_section_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("note_templates.id"), nullable=False
        ),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("translated_structure", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("template_id", "language", name="uq_template_translation_language"),
    )
    op.create_index(
        "ix_template_section_translations_template_id", "template_section_translations", ["template_id"]
    )

    op.create_table(
        "patient_share_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("sent_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_patient_share_logs_encounter_id", "patient_share_logs", ["encounter_id"])

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("video_storage_path", sa.String(1000), nullable=True),
        sa.Column("video_mime_type", sa.String(100), nullable=True),
        sa.Column("video_original_filename", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_announcements_clinic_id", "announcements", ["clinic_id"])

    op.create_table(
        "announcement_acknowledgments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "announcement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("announcements.id"), nullable=False
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_ack_user"),
    )
    op.create_index(
        "ix_announcement_acknowledgments_announcement_id", "announcement_acknowledgments", ["announcement_id"]
    )
    op.create_index("ix_announcement_acknowledgments_user_id", "announcement_acknowledgments", ["user_id"])


def downgrade() -> None:
    op.drop_table("announcement_acknowledgments")
    op.drop_table("announcements")
    op.drop_table("patient_share_logs")
    op.drop_table("template_section_translations")
    op.drop_table("daily_recaps")
