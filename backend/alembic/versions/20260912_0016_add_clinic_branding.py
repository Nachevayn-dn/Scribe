"""White-label branding override, per clinic: a nullable logo_url +
branding_name on clinics. Null means "show the default MedicDesk.ai logo and
wordmark" — the behavior every clinic has today. Only set by a platform
admin (see POST/DELETE /platform/clinics/{id}/logo, and branding_name on
PATCH /platform/clinics/{id}) — never by a clinic's own SUPER_ADMIN.

Revision ID: 0016_add_clinic_branding
Revises: 0015_add_batch_features
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016_add_clinic_branding"
down_revision: Union[str, None] = "0015_add_batch_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("logo_url", sa.String(length=500), nullable=True))
    op.add_column("clinics", sa.Column("branding_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "branding_name")
    op.drop_column("clinics", "logo_url")
