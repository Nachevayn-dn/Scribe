"""add TRANSCRIPT_READY to encounter_status enum

Revision ID: 0003_add_transcript_ready_status
Revises: 0002_seed_global_templates
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_transcript_ready_status"
down_revision: Union[str, None] = "0002_seed_global_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE encounter_status ADD VALUE IF NOT EXISTS 'TRANSCRIPT_READY'")


def downgrade() -> None:
    # Postgres does not support removing an enum value. A downgrade would
    # need to recreate the type; left as a no-op since no data migration
    # depends on this (encounters simply stop passing through this status).
    pass
