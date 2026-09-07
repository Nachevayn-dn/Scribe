"""widen inbound_call_sessions.from_number to fit whatsapp: prefixed numbers

Revision ID: 0011_widen_call_from_number
Revises: 0010_add_inbound_outbound_agents
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_widen_call_from_number"
down_revision: Union[str, None] = "0010_add_inbound_outbound_agents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # "whatsapp:+15550001234" is longer than a bare E.164 number — the
    # original String(20) was sized for phone calls only and truncates
    # WhatsApp senders. 30 matches inbound_agent_configs.whatsapp_number.
    op.alter_column(
        "inbound_call_sessions", "from_number", type_=sa.String(30), existing_type=sa.String(20)
    )


def downgrade() -> None:
    op.alter_column(
        "inbound_call_sessions", "from_number", type_=sa.String(20), existing_type=sa.String(30)
    )
