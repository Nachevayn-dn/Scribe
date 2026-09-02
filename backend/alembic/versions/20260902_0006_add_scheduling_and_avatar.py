"""add encounter scheduling fields and user photo_url

Revision ID: 0006_add_scheduling_and_avatar
Revises: 0005_add_encounter_language
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_add_scheduling_and_avatar"
down_revision: Union[str, None] = "0005_add_encounter_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "encounters",
        sa.Column(
            "is_scheduled_appointment",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "encounters", sa.Column("appointment_time", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("photo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "photo_url")
    op.drop_column("encounters", "appointment_time")
    op.drop_column("encounters", "is_scheduled_appointment")
