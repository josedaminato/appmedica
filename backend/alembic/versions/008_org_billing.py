"""organization billing fields

Revision ID: 008
Revises: 007
Create Date: 2026-07-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("service_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("organizations", sa.Column("paid_until", sa.Date(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("monthly_fee", sa.Numeric(12, 2), nullable=False, server_default="25000"),
    )

    op.execute(
        """
        UPDATE organizations
        SET service_started_at = created_at,
            paid_until = (created_at + INTERVAL '1 month')::date
        WHERE service_started_at IS NULL
        """
    )

    op.alter_column("organizations", "service_started_at", nullable=False)
    op.alter_column("organizations", "monthly_fee", server_default=None)


def downgrade() -> None:
    op.drop_column("organizations", "monthly_fee")
    op.drop_column("organizations", "paid_until")
    op.drop_column("organizations", "service_started_at")
