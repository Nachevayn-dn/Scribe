"""seed global note templates

Revision ID: 0002_seed_global_templates
Revises: 0001_initial_schema
Create Date: 2026-09-01

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_seed_global_templates"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATES_TABLE = sa.table(
    "note_templates",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("clinic_id", postgresql.UUID(as_uuid=True)),
    sa.column("created_by_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("template_type", postgresql.ENUM(name="template_type", create_type=False)),
    sa.column("structure", postgresql.JSONB),
    sa.column("is_active", sa.Boolean),
)

# Fixed IDs so this migration is idempotent / easy to reference from seed data.
CLINICAL_SUMMARY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
REFERRAL_LETTER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def upgrade() -> None:
    op.bulk_insert(
        TEMPLATES_TABLE,
        [
            {
                "id": CLINICAL_SUMMARY_ID,
                "clinic_id": None,
                "created_by_id": None,
                "name": "Clinical Summary",
                "template_type": "CLINICAL_SUMMARY",
                "structure": ["Intake", "Diagnostics", "Next Steps", "Close"],
                "is_active": True,
            },
            {
                "id": REFERRAL_LETTER_ID,
                "clinic_id": None,
                "created_by_id": None,
                "name": "Referral Letter",
                "template_type": "REFERRAL_LETTER",
                "structure": ["Reason for Referral", "Clinical History", "Findings", "Recommendation"],
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        TEMPLATES_TABLE.delete().where(
            TEMPLATES_TABLE.c.id.in_([CLINICAL_SUMMARY_ID, REFERRAL_LETTER_ID])
        )
    )
