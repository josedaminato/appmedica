"""Consultation integrity: RESTRICT FK, professional snapshot, immutability, amends_id.

Revision ID: 013
Revises: 012
Create Date: 2026-09-11

Aditiva y reversible. No modifica 011. No altera filas existentes:
snapshot y amends_id quedan NULL; license_number de users queda NULL.

Cambiar ON DELETE CASCADE → RESTRICT no exige limpieza de datos: la FK
actual ya impide consultas huérfanas. Si hubiera inconsistencias, upgrade
falla sin borrar ni reescribir filas.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPOINTMENT_FK = "consultations_appointment_id_fkey"
AMENDS_FK = "fk_consultations_amends_id"

PREVENT_FINALIZED_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_finalized_consultation_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.status::text = 'finalized' THEN
      RAISE EXCEPTION 'Finalized consultations cannot be deleted'
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN OLD;
  END IF;

  IF OLD.status::text = 'finalized' THEN
    RAISE EXCEPTION 'Finalized consultations cannot be modified'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""

DROP_FINALIZED_IMMUTABLE_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_consultations_finalized_immutable ON consultations
"""

CREATE_FINALIZED_IMMUTABLE_TRIGGER_SQL = """
CREATE TRIGGER trg_consultations_finalized_immutable
BEFORE UPDATE OR DELETE ON consultations
FOR EACH ROW
EXECUTE PROCEDURE prevent_finalized_consultation_mutation()
"""

DROP_PREVENT_FINALIZED_MUTATION_FUNCTION_SQL = """
DROP FUNCTION IF EXISTS prevent_finalized_consultation_mutation()
"""


def upgrade() -> None:
    conn = op.get_bind()
    orphans = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM consultations c
            LEFT JOIN appointments a ON a.id = c.appointment_id
            WHERE a.id IS NULL
            """
        )
    ).scalar()
    if orphans:
        raise RuntimeError(
            f"No se puede aplicar 013: hay {orphans} consulta(s) sin turno. "
            "No se alteran datos automáticamente."
        )

    op.drop_constraint(APPOINTMENT_FK, "consultations", type_="foreignkey")
    op.create_foreign_key(
        APPOINTMENT_FK,
        "consultations",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "users",
        sa.Column("license_number", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "consultations",
        sa.Column("professional_name_snapshot", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "consultations",
        sa.Column("professional_license_snapshot", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "consultations",
        sa.Column("amends_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_consultations_amends_id", "consultations", ["amends_id"])
    op.create_foreign_key(
        AMENDS_FK,
        "consultations",
        "consultations",
        ["amends_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(PREVENT_FINALIZED_MUTATION_FUNCTION_SQL)
    op.execute(DROP_FINALIZED_IMMUTABLE_TRIGGER_SQL)
    op.execute(CREATE_FINALIZED_IMMUTABLE_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(DROP_FINALIZED_IMMUTABLE_TRIGGER_SQL)
    op.execute(DROP_PREVENT_FINALIZED_MUTATION_FUNCTION_SQL)

    op.drop_constraint(AMENDS_FK, "consultations", type_="foreignkey")
    op.drop_index("ix_consultations_amends_id", table_name="consultations")
    op.drop_column("consultations", "amends_id")
    op.drop_column("consultations", "professional_license_snapshot")
    op.drop_column("consultations", "professional_name_snapshot")
    op.drop_column("users", "license_number")

    op.drop_constraint(APPOINTMENT_FK, "consultations", type_="foreignkey")
    op.create_foreign_key(
        APPOINTMENT_FK,
        "consultations",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="CASCADE",
    )
