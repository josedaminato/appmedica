"""consultations table and patient clinical profile fields

Revision ID: 011
Revises: 010
Create Date: 2026-09-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

consultation_status_enum = postgresql.ENUM(
    "draft",
    "finalized",
    name="consultation_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE consultation_status AS ENUM ('draft', 'finalized')")

    op.add_column("patients", sa.Column("medical_history", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("allergies", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("current_medications", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("clinical_notes", sa.Text(), nullable=True))

    op.create_table(
        "consultations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evolution", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("indications", sa.Text(), nullable=True),
        sa.Column(
            "status",
            consultation_status_enum,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id", name="uq_consultations_appointment_id"),
    )
    op.create_index("ix_consultations_organization_id", "consultations", ["organization_id"])
    op.create_index("ix_consultations_patient_id", "consultations", ["patient_id"])
    op.create_index("ix_consultations_professional_id", "consultations", ["professional_id"])
    op.create_index("ix_consultations_status", "consultations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_consultations_status", table_name="consultations")
    op.drop_index("ix_consultations_professional_id", table_name="consultations")
    op.drop_index("ix_consultations_patient_id", table_name="consultations")
    op.drop_index("ix_consultations_organization_id", table_name="consultations")
    op.drop_table("consultations")
    op.drop_column("patients", "clinical_notes")
    op.drop_column("patients", "current_medications")
    op.drop_column("patients", "allergies")
    op.drop_column("patients", "medical_history")
    op.execute("DROP TYPE consultation_status")
