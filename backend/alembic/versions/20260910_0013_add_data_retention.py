"""data retention: per-doctor "retain all sessions" override, a provider
scope on clinic documents (for the signed consent form that grants it), and
a purge marker on Encounter — see services/retention_service.py.

Revision ID: 0013_add_data_retention
Revises: 0012_add_password_setup_token
Create Date: 2026-09-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_add_data_retention"
down_revision: Union[str, None] = "0012_add_password_setup_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("retain_all_sessions", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "clinic_documents",
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_clinic_documents_provider_id", "clinic_documents", ["provider_id"])
    op.create_foreign_key(
        "fk_clinic_documents_provider_id_users",
        "clinic_documents",
        "users",
        ["provider_id"],
        ["id"],
    )
    op.add_column(
        "encounters",
        sa.Column("content_purged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("encounters", "content_purged_at")
    op.drop_constraint("fk_clinic_documents_provider_id_users", "clinic_documents", type_="foreignkey")
    op.drop_index("ix_clinic_documents_provider_id", table_name="clinic_documents")
    op.drop_column("clinic_documents", "provider_id")
    op.drop_column("users", "retain_all_sessions")
