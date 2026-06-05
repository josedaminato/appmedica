"""calendar feed token on users

Revision ID: 004
Revises: 003
Create Date: 2026-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("calendar_feed_token", sa.String(64), nullable=True))
    op.create_index("ix_users_calendar_feed_token", "users", ["calendar_feed_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_calendar_feed_token", table_name="users")
    op.drop_column("users", "calendar_feed_token")
