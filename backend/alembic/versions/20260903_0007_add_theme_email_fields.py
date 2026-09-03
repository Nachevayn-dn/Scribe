"""add theme preference, notification email, clinic contact/staff email

Revision ID: 0007_add_theme_email_fields
Revises: 0006_add_scheduling_and_avatar
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_add_theme_email_fields"
down_revision: Union[str, None] = "0006_add_scheduling_and_avatar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_preference", sa.String(20), nullable=False, server_default="midnight"),
    )
    op.add_column("users", sa.Column("notification_email", sa.String(255), nullable=True))
    op.add_column("clinics", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column("clinics", sa.Column("staff_email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "staff_email")
    op.drop_column("clinics", "contact_email")
    op.drop_column("users", "notification_email")
    op.drop_column("users", "theme_preference")
