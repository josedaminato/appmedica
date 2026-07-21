import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import pg_enum
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
)


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "appointments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    health_insurance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_insurances.id", ondelete="SET NULL"),
        nullable=True,
    )
    rescheduled_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"),
        default=AppointmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    modality: Mapped[AppointmentModality] = mapped_column(
        pg_enum(AppointmentModality, "appointment_modality"),
        default=AppointmentModality.IN_PERSON,
        nullable=False,
    )
    attention_type: Mapped[AttentionType] = mapped_column(
        pg_enum(AttentionType, "attention_type"),
        default=AttentionType.PRIVATE,
        nullable=False,
    )
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    closure_status: Mapped[AppointmentClosureStatus] = mapped_column(
        pg_enum(AppointmentClosureStatus, "appointment_closure_status"),
        default=AppointmentClosureStatus.NONE,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship(foreign_keys=[patient_id])
    professional: Mapped["User | None"] = relationship(foreign_keys=[professional_id])
    health_insurance: Mapped["HealthInsurance | None"] = relationship(
        foreign_keys=[health_insurance_id],
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="appointment")
