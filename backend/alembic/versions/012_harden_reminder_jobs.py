"""Harden reminder_jobs: appointment FK, active unique, retry/audit columns.

Revision ID: 012
Revises: 011
Create Date: 2026-09-10

Jobs existentes: appointment_id se rellena desde payload->>'appointment_id'
si el turno existe en la misma organización. Duplicados activos se cancelan
(error_code=deduped_pre_unique). Filas sin turno reconstruible se eliminan
(no se pueden enviar ni auditar con integridad referencial).

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

reminder_kind_enum = postgresql.ENUM(
    "appointment_reminder_24h",
    name="reminder_kind",
    create_type=False,
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE reminder_status ADD VALUE IF NOT EXISTS 'sending'")
        op.execute("ALTER TYPE reminder_status ADD VALUE IF NOT EXISTS 'skipped'")

    op.execute("CREATE TYPE reminder_kind AS ENUM ('appointment_reminder_24h')")

    op.add_column(
        "reminder_jobs",
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column(
            "kind",
            reminder_kind_enum,
            nullable=False,
            server_default="appointment_reminder_24h",
        ),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column("provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "reminder_jobs",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )

    op.execute(
        """
        UPDATE reminder_jobs AS j
        SET appointment_id = a.id
        FROM appointments AS a
        WHERE j.appointment_id IS NULL
          AND j.payload ? 'appointment_id'
          AND j.payload->>'appointment_id' = a.id::text
          AND j.organization_id = a.organization_id
        """
    )
    op.execute(
        """
        UPDATE reminder_jobs
        SET next_attempt_at = scheduled_at
        WHERE next_attempt_at IS NULL
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY appointment_id, kind, channel
                       ORDER BY created_at DESC
                   ) AS rn
            FROM reminder_jobs
            WHERE appointment_id IS NOT NULL
              AND status IN ('scheduled', 'sending', 'sent')
        )
        UPDATE reminder_jobs AS j
        SET status = 'cancelled',
            error_code = 'deduped_pre_unique',
            error_message = 'Duplicate active job collapsed during 012 migration'
        FROM ranked
        WHERE j.id = ranked.id
          AND ranked.rn > 1
        """
    )
    op.execute(
        """
        DELETE FROM reminder_jobs
        WHERE appointment_id IS NULL
        """
    )

    op.alter_column("reminder_jobs", "appointment_id", nullable=False)
    op.alter_column("reminder_jobs", "next_attempt_at", nullable=False)
    op.alter_column("reminder_jobs", "kind", server_default=None)
    op.alter_column("reminder_jobs", "attempt_count", server_default=None)

    op.create_foreign_key(
        "fk_reminder_jobs_appointment_id",
        "reminder_jobs",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_reminder_jobs_appointment_id",
        "reminder_jobs",
        ["appointment_id"],
    )
    op.create_index(
        "ix_reminder_jobs_status_next_attempt_at",
        "reminder_jobs",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "uq_reminder_jobs_active_appointment_kind_channel",
        "reminder_jobs",
        ["appointment_id", "kind", "channel"],
        unique=True,
        postgresql_where=sa.text("status IN ('scheduled', 'sending', 'sent')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_reminder_jobs_active_appointment_kind_channel",
        table_name="reminder_jobs",
    )
    op.drop_index("ix_reminder_jobs_status_next_attempt_at", table_name="reminder_jobs")
    op.drop_index("ix_reminder_jobs_appointment_id", table_name="reminder_jobs")
    op.drop_constraint("fk_reminder_jobs_appointment_id", "reminder_jobs", type_="foreignkey")
    op.drop_column("reminder_jobs", "error_code")
    op.drop_column("reminder_jobs", "provider")
    op.drop_column("reminder_jobs", "attempt_count")
    op.drop_column("reminder_jobs", "sent_at")
    op.drop_column("reminder_jobs", "next_attempt_at")
    op.drop_column("reminder_jobs", "kind")
    op.drop_column("reminder_jobs", "appointment_id")
    op.execute("DROP TYPE reminder_kind")
