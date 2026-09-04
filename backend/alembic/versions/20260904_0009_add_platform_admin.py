"""platform admin support: nullable user password, language pref, is_platform_admin, clinic_documents

Revision ID: 0009_add_platform_admin
Revises: 0008_add_appointments
Create Date: 2026-09-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009_add_platform_admin"
down_revision: Union[str, None] = "0008_add_appointments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("password_set_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("language_preference", sa.String(10), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Existing accounts all already have a password — backfill password_set_at
    # so they read as "credentials generated" rather than "pending."
    op.execute("UPDATE users SET password_set_at = created_at WHERE hashed_password IS NOT NULL")

    op.create_table(
        "clinic_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum("CONTRACT", "ORDER_FORM", "CONSENT_FORM", name="clinic_document_type"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clinic_documents_clinic_id", "clinic_documents", ["clinic_id"])


def downgrade() -> None:
    op.drop_index("ix_clinic_documents_clinic_id", table_name="clinic_documents")
    op.drop_table("clinic_documents")
    op.execute("DROP TYPE IF EXISTS clinic_document_type")
    op.drop_column("users", "is_platform_admin")
    op.drop_column("users", "language_preference")
    op.drop_column("users", "password_set_at")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
