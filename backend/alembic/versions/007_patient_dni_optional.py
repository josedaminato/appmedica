"""patient dni optional

Revision ID: 007
Revises: 006
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_patients_org_dni", "patients", type_="unique")
    op.alter_column("patients", "dni", existing_type=sa.String(20), nullable=True)
    op.create_index(
        "uq_patients_org_dni_not_null",
        "patients",
        ["organization_id", "dni"],
        unique=True,
        postgresql_where=sa.text("dni IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_patients_org_dni_not_null", table_name="patients")
    op.alter_column("patients", "dni", existing_type=sa.String(20), nullable=False)
    op.create_unique_constraint("uq_patients_org_dni", "patients", ["organization_id", "dni"])
