"""two-stage retention: archived_at marks stage 1 (audio purged, moved out
of the active session list) separately from content_purged_at (stage 2 —
transcript+note purged at the ~7-year regulatory floor). See
services/retention_service.py.

Revision ID: 0014_add_encounter_archived_at
Revises: 0013_add_data_retention
Create Date: 2026-09-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_add_encounter_archived_at"
down_revision: Union[str, None] = "0013_add_data_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "encounters",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("encounters", "archived_at")
