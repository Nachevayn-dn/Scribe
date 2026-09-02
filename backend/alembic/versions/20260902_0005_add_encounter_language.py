"""add language column to encounters

Revision ID: 0005_add_encounter_language
Revises: 0004_add_transcript_entities
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_add_encounter_language"
down_revision: Union[str, None] = "0004_add_transcript_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("encounters", sa.Column("language", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("encounters", "language")
