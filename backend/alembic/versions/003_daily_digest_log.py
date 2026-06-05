"""daily digest log for professional agenda emails

Revision ID: 003
Revises: 002
Create Date: 2026-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_digest_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_date", name="uq_daily_digest_user_date"),
    )
    op.create_index("ix_daily_digest_logs_organization_id", "daily_digest_logs", ["organization_id"])
    op.create_index("ix_daily_digest_logs_user_id", "daily_digest_logs", ["user_id"])
    op.create_index("ix_daily_digest_logs_target_date", "daily_digest_logs", ["target_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_digest_logs_target_date", table_name="daily_digest_logs")
    op.drop_index("ix_daily_digest_logs_user_id", table_name="daily_digest_logs")
    op.drop_index("ix_daily_digest_logs_organization_id", table_name="daily_digest_logs")
    op.drop_table("daily_digest_logs")
