"""Add missing non-unique index on consultations.appointment_id.

Revision ID: 016
Revises: 015
Create Date: 2026-09-14

015 persistente se aplicó antes de que el archivo 015 creara este índice.
Aditiva e idempotente. No modifica 011-015 ni datos clínicos.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_consultations_appointment_id"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "consultations",
        ["appointment_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="consultations", if_exists=True)
