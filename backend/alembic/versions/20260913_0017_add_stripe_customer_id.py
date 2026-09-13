"""Billing: a nullable stripe_customer_id on clinics, created lazily the
first time a clinic's SUPER_ADMIN uses "Payment details" (Settings page).
We never store raw card data ourselves — see services/billing_service.py.

Revision ID: 0017_add_stripe_customer_id
Revises: 0016_add_clinic_branding
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. Kept under 32 chars —
# alembic_version.version_num is varchar(32) by default.
revision: str = "0017_add_stripe_customer_id"
down_revision: Union[str, None] = "0016_add_clinic_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "stripe_customer_id")
