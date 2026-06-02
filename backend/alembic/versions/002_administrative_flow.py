"""administrative flow phase 2

Revision ID: 002
Revises: 001
Create Date: 2026-05-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New enum types
    op.execute("CREATE TYPE appointment_modality AS ENUM ('presencial', 'online')")
    op.execute("CREATE TYPE attention_type AS ENUM ('private', 'health_insurance')")
    op.execute(
        "CREATE TYPE appointment_closure_status AS ENUM "
        "('none', 'paid', 'pending', 'partial', 'insurance_pending')"
    )
    op.execute("ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'rescheduled'")
    op.execute("ALTER TYPE insurance_claim_status ADD VALUE IF NOT EXISTS 'rejected'")

    # Appointments extensions
    op.add_column(
        "appointments",
        sa.Column(
            "modality",
            sa.Enum("presencial", "online", name="appointment_modality"),
            nullable=False,
            server_default="presencial",
        ),
    )
    op.add_column(
        "appointments",
        sa.Column(
            "attention_type",
            sa.Enum("private", "health_insurance", name="attention_type"),
            nullable=False,
            server_default="private",
        ),
    )
    op.add_column("appointments", sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "appointments",
        sa.Column(
            "closure_status",
            sa.Enum(
                "none", "paid", "pending", "partial", "insurance_pending",
                name="appointment_closure_status",
            ),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "appointments",
        sa.Column("health_insurance_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("rescheduled_to_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_appointments_health_insurance",
        "appointments",
        "health_insurances",
        ["health_insurance_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_appointments_rescheduled_to",
        "appointments",
        "appointments",
        ["rescheduled_to_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_appointments_closure_status", "appointments", ["closure_status"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])

    # Payments: link to appointment
    op.add_column(
        "payments",
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payments_appointment",
        "payments",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_payments_appointment_id", "payments", ["appointment_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    # Insurance claims extensions
    op.add_column(
        "insurance_claims",
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "insurance_claims",
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column("insurance_claims", sa.Column("service_date", sa.Date(), nullable=True))
    op.add_column(
        "insurance_claims",
        sa.Column("invoiced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "insurance_claims",
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("insurance_claims", sa.Column("notes", sa.Text(), nullable=True))
    op.execute(
        "UPDATE insurance_claims SET expected_amount = amount, "
        "service_date = created_at::date WHERE expected_amount IS NULL"
    )
    op.alter_column("insurance_claims", "expected_amount", nullable=False)
    op.alter_column("insurance_claims", "service_date", nullable=False)
    op.drop_column("insurance_claims", "amount")
    op.create_foreign_key(
        "fk_insurance_claims_appointment",
        "insurance_claims",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_insurance_claims_appointment_id", "insurance_claims", ["appointment_id"])
    op.create_index("ix_insurance_claims_status", "insurance_claims", ["status"])


def downgrade() -> None:
    op.drop_index("ix_insurance_claims_status", "insurance_claims")
    op.drop_index("ix_insurance_claims_appointment_id", "insurance_claims")
    op.drop_constraint("fk_insurance_claims_appointment", "insurance_claims", type_="foreignkey")
    op.add_column("insurance_claims", sa.Column("amount", sa.Numeric(12, 2), nullable=True))
    op.execute("UPDATE insurance_claims SET amount = expected_amount")
    op.drop_column("insurance_claims", "notes")
    op.drop_column("insurance_claims", "collected_at")
    op.drop_column("insurance_claims", "invoiced_at")
    op.drop_column("insurance_claims", "service_date")
    op.drop_column("insurance_claims", "expected_amount")
    op.drop_column("insurance_claims", "appointment_id")

    op.drop_index("ix_payments_status", "payments")
    op.drop_index("ix_payments_appointment_id", "payments")
    op.drop_constraint("fk_payments_appointment", "payments", type_="foreignkey")
    op.drop_column("payments", "appointment_id")

    op.drop_index("ix_appointments_patient_id", "appointments")
    op.drop_index("ix_appointments_status", "appointments")
    op.drop_index("ix_appointments_closure_status", "appointments")
    op.drop_constraint("fk_appointments_rescheduled_to", "appointments", type_="foreignkey")
    op.drop_constraint("fk_appointments_health_insurance", "appointments", type_="foreignkey")
    op.drop_column("appointments", "rescheduled_to_id")
    op.drop_column("appointments", "health_insurance_id")
    op.drop_column("appointments", "closure_status")
    op.drop_column("appointments", "expected_amount")
    op.drop_column("appointments", "attention_type")
    op.drop_column("appointments", "modality")

    op.execute("DROP TYPE IF EXISTS appointment_closure_status")
    op.execute("DROP TYPE IF EXISTS attention_type")
    op.execute("DROP TYPE IF EXISTS appointment_modality")
