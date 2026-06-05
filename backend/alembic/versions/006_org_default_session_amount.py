"""default private session amount on organization

Revision ID: 006
Revises: 005
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("default_private_session_amount", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "default_private_session_amount")
