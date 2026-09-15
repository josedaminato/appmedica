"""DDL de integridad de consultations para tests PostgreSQL aislados.

Las migraciones Alembic 013 y 015 instalan el mismo DDL de forma autosuficiente.
Este módulo no se usa en runtime ni por Alembic.
"""

from sqlalchemy import text

CONSULTATION_IMMUTABILITY_FUNCTION_SQL = """
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

CONSULTATION_IMMUTABILITY_DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_consultations_finalized_immutable ON consultations
"""

CONSULTATION_IMMUTABILITY_CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_consultations_finalized_immutable
BEFORE UPDATE OR DELETE ON consultations
FOR EACH ROW
EXECUTE PROCEDURE prevent_finalized_consultation_mutation()
"""

CONSULTATION_IMMUTABILITY_DROP_FUNCTION_SQL = """
DROP FUNCTION IF EXISTS prevent_finalized_consultation_mutation()
"""


CONSULTATION_AMENDS_ORIGINAL_FUNCTION_SQL = """
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

CONSULTATION_AMENDS_ORIGINAL_DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_consultations_amends_original ON consultations
"""

CONSULTATION_AMENDS_ORIGINAL_CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_consultations_amends_original
BEFORE INSERT OR UPDATE OF amends_id, organization_id ON consultations
FOR EACH ROW
EXECUTE PROCEDURE prevent_consultation_amendment_chain()
"""

CONSULTATION_AMENDS_ORIGINAL_DROP_FUNCTION_SQL = """
DROP FUNCTION IF EXISTS prevent_consultation_amendment_chain()
"""

CONSULTATION_BACKFILL_OCCURRED_AT_FROM_APPOINTMENT_SQL = """
UPDATE consultations AS c
SET occurred_at = a.start_at
FROM appointments AS a
WHERE c.occurred_at IS NULL
  AND c.appointment_id = a.id
"""

CONSULTATION_BACKFILL_OCCURRED_AT_FROM_CREATED_AT_SQL = """
UPDATE consultations
SET occurred_at = created_at
WHERE occurred_at IS NULL
"""


def apply_consultation_immutability_ddl(connection) -> None:
    connection.execute(text(CONSULTATION_IMMUTABILITY_FUNCTION_SQL))
    connection.execute(text(CONSULTATION_IMMUTABILITY_DROP_TRIGGER_SQL))
    connection.execute(text(CONSULTATION_IMMUTABILITY_CREATE_TRIGGER_SQL))


def drop_consultation_immutability_ddl(connection) -> None:
    connection.execute(text(CONSULTATION_IMMUTABILITY_DROP_TRIGGER_SQL))
    connection.execute(text(CONSULTATION_IMMUTABILITY_DROP_FUNCTION_SQL))


def apply_consultation_amendment_chain_ddl(connection) -> None:
    connection.execute(text(CONSULTATION_AMENDS_ORIGINAL_FUNCTION_SQL))
    connection.execute(text(CONSULTATION_AMENDS_ORIGINAL_DROP_TRIGGER_SQL))
    connection.execute(text(CONSULTATION_AMENDS_ORIGINAL_CREATE_TRIGGER_SQL))


def drop_consultation_amendment_chain_ddl(connection) -> None:
    connection.execute(text(CONSULTATION_AMENDS_ORIGINAL_DROP_TRIGGER_SQL))
    connection.execute(text(CONSULTATION_AMENDS_ORIGINAL_DROP_FUNCTION_SQL))
