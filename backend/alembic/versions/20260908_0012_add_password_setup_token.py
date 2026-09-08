"""password setup token: lets a doctor set their own password via an emailed
link, instead of a platform admin generating and copying a temp password.

Revision ID: 0012_add_password_setup_token
Revises: 0011_widen_call_from_number
Create Date: 2026-09-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_add_password_setup_token"
down_revision: Union[str, None] = "0011_widen_call_from_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_setup_token_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("password_setup_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_password_setup_token_hash", "users", ["password_setup_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_password_setup_token_hash", table_name="users")
    op.drop_column("users", "password_setup_expires_at")
    op.drop_column("users", "password_setup_token_hash")
