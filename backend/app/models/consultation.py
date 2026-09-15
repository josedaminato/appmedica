import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import pg_enum
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConsultationStatus


class Consultation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "consultations"
    __table_args__ = (
        Index(
            "uq_consultations_primary_appointment_id",
            "appointment_id",
            unique=True,
            postgresql_where=text("appointment_id IS NOT NULL AND amends_id IS NULL"),
            sqlite_where=text("appointment_id IS NOT NULL AND amends_id IS NULL"),
        ),
        CheckConstraint(
            "(amends_id IS NULL AND amend_reason IS NULL) OR "
            "(amends_id IS NOT NULL AND amend_reason IS NOT NULL "
            "AND trim(amend_reason) <> '')",
            name="ck_consultations_amend_reason",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    indications: Mapped[str | None] = mapped_column(Text, nullable=True)
    amend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    professional_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    professional_license_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amends_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    status: Mapped[ConsultationStatus] = mapped_column(
        pg_enum(ConsultationStatus, "consultation_status"),
        default=ConsultationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    appointment: Mapped["Appointment | None"] = relationship(foreign_keys=[appointment_id])
    patient: Mapped["Patient"] = relationship(foreign_keys=[patient_id])
    professional: Mapped["User"] = relationship(foreign_keys=[professional_id])
