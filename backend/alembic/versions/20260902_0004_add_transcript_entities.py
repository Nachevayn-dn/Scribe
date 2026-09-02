"""add transcript_entities table

Revision ID: 0004_add_transcript_entities
Revises: 0003_add_transcript_ready_status
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_add_transcript_entities"
down_revision: Union[str, None] = "0003_add_transcript_ready_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reuses the existing "entity_type" enum (created in 0001 for
    # note_entities) — same Python EntityType, same five values.
    entity_type = postgresql.ENUM(name="entity_type", create_type=False)

    op.create_table(
        "transcript_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transcript_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcripts.id"), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column("line_index", sa.Integer, nullable=False),
        sa.Column("start_offset", sa.Integer, nullable=True),
        sa.Column("end_offset", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_transcript_entities_transcript_id", "transcript_entities", ["transcript_id"])


def downgrade() -> None:
    op.drop_table("transcript_entities")
