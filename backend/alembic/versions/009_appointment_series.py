"""appointment series_id for fixed weekly turns

Revision ID: 009
Revises: 008
Create Date: 2026-07-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_appointments_series_id", "appointments", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_appointments_series_id", table_name="appointments")
    op.drop_column("appointments", "series_id")
