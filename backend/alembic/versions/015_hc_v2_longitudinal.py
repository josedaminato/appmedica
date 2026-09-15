"""HC v2: nullable appointment, primary unique, occurred_at, amend_reason.

Revision ID: 015
Revises: 014
Create Date: 2026-09-14

No modifica 011, 013 ni 014. Backfill de occurred_at; filas existentes
siguen siendo consultas primarias (appointment_id NOT NULL, amends_id NULL).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRIMARY_UNIQUE = "uq_consultations_primary_appointment_id"
AMEND_REASON_CHECK = "ck_consultations_amend_reason"
AMENDS_ORIGINAL_FUNCTION = "prevent_consultation_amendment_chain"
AMENDS_ORIGINAL_TRIGGER = "trg_consultations_amends_original"

BACKFILL_FROM_APPOINTMENT_SQL = """
UPDATE consultations AS c
SET occurred_at = a.start_at
FROM appointments AS a
WHERE c.occurred_at IS NULL
  AND c.appointment_id = a.id
"""

BACKFILL_FROM_CREATED_AT_SQL = """
UPDATE consultations
SET occurred_at = created_at
WHERE occurred_at IS NULL
"""

AMENDS_ORIGINAL_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_consultation_amendment_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.amends_id IS NULL THEN
    RETURN NEW;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM consultations AS original
    WHERE original.id = NEW.amends_id
      AND original.amends_id IS NULL
      AND original.organization_id = NEW.organization_id
  ) THEN
    RAISE EXCEPTION 'amends_id must reference an original consultation in the same organization'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""

AMENDS_ORIGINAL_DROP_TRIGGER_SQL = (
    f"DROP TRIGGER IF EXISTS {AMENDS_ORIGINAL_TRIGGER} ON consultations"
)

AMENDS_ORIGINAL_CREATE_TRIGGER_SQL = f"""
CREATE TRIGGER {AMENDS_ORIGINAL_TRIGGER}
BEFORE INSERT OR UPDATE OF amends_id, organization_id ON consultations
FOR EACH ROW
EXECUTE PROCEDURE prevent_consultation_amendment_chain()
"""


def _drop_absolute_appointment_uniques() -> None:
    conn = op.get_bind()
    constraints = conn.execute(
        sa.text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = current_schema()
              AND rel.relname = 'consultations'
              AND c.contype = 'u'
              AND pg_get_constraintdef(c.oid) ILIKE '%appointment_id%'
              AND pg_get_constraintdef(c.oid) NOT ILIKE '%amends_id%'
            """
        )
    ).fetchall()
    dropped = {row[0] for row in constraints}
    for name in dropped:
        op.drop_constraint(name, "consultations", type_="unique")

    indexes = conn.execute(
        sa.text(
            """
            SELECT idx.relname
            FROM pg_index x
            JOIN pg_class idx ON idx.oid = x.indexrelid
            JOIN pg_class tbl ON tbl.oid = x.indrelid
            JOIN pg_namespace nsp ON nsp.oid = tbl.relnamespace
            WHERE nsp.nspname = current_schema()
              AND tbl.relname = 'consultations'
              AND x.indisunique
              AND NOT x.indisprimary
              AND pg_get_indexdef(x.indexrelid) ILIKE '%appointment_id%'
              AND pg_get_indexdef(x.indexrelid) NOT ILIKE '%amends_id%'
            """
        )
    ).fetchall()
    for (name,) in indexes:
        if name not in dropped:
            op.drop_index(name, table_name="consultations")


def upgrade() -> None:
    op.add_column("consultations", sa.Column("amend_reason", sa.Text(), nullable=True))
    op.add_column(
        "consultations",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consultations_occurred_at", "consultations", ["occurred_at"])

    op.execute(BACKFILL_FROM_APPOINTMENT_SQL)
    op.execute(BACKFILL_FROM_CREATED_AT_SQL)

    _drop_absolute_appointment_uniques()
    op.alter_column(
        "consultations",
        "appointment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        "ix_consultations_appointment_id",
        "consultations",
        ["appointment_id"],
    )
    op.create_index(
        PRIMARY_UNIQUE,
        "consultations",
        ["appointment_id"],
        unique=True,
        postgresql_where=sa.text("appointment_id IS NOT NULL AND amends_id IS NULL"),
    )
    op.create_check_constraint(
        AMEND_REASON_CHECK,
        "consultations",
        "(amends_id IS NULL AND amend_reason IS NULL) OR "
        "(amends_id IS NOT NULL AND amend_reason IS NOT NULL AND trim(amend_reason) <> '')",
    )
    op.execute(AMENDS_ORIGINAL_FUNCTION_SQL)
    op.execute(AMENDS_ORIGINAL_DROP_TRIGGER_SQL)
    op.execute(AMENDS_ORIGINAL_CREATE_TRIGGER_SQL)


def downgrade() -> None:
    conn = op.get_bind()
    nulls = conn.execute(
        sa.text("SELECT COUNT(*) FROM consultations WHERE appointment_id IS NULL")
    ).scalar()
    if nulls:
        raise RuntimeError(
            f"No se puede revertir 015: hay {nulls} consulta(s) sin turno."
        )

    op.execute(AMENDS_ORIGINAL_DROP_TRIGGER_SQL)
    op.execute(f"DROP FUNCTION IF EXISTS {AMENDS_ORIGINAL_FUNCTION}()")
    op.drop_constraint(AMEND_REASON_CHECK, "consultations", type_="check")
    op.drop_index(PRIMARY_UNIQUE, table_name="consultations")
    op.drop_index("ix_consultations_appointment_id", table_name="consultations")
    op.alter_column(
        "consultations",
        "appointment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_consultations_appointment_id",
        "consultations",
        ["appointment_id"],
    )
    op.drop_index("ix_consultations_occurred_at", table_name="consultations")
    op.drop_column("consultations", "occurred_at")
    op.drop_column("consultations", "amend_reason")
