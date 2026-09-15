"""Clinical profile authorship: clinical_updated_by / clinical_updated_at.

Revision ID: 014
Revises: 013
Create Date: 2026-09-14

Aditiva y reversible. No modifica 011 ni 013. Filas existentes quedan con
autor y fecha NULL (sin backfill).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLINICAL_UPDATED_BY_FK = "fk_patients_clinical_updated_by"


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("clinical_updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("clinical_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        CLINICAL_UPDATED_BY_FK,
        "patients",
        "users",
        ["clinical_updated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(CLINICAL_UPDATED_BY_FK, "patients", type_="foreignkey")
    op.drop_column("patients", "clinical_updated_at")
    op.drop_column("patients", "clinical_updated_by")
