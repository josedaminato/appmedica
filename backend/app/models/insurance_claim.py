import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import pg_enum
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InsuranceClaimStatus


class InsuranceClaim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "insurance_claims"

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
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    health_insurance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_insurances.id", ondelete="CASCADE"),
        nullable=False,
    )
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InsuranceClaimStatus] = mapped_column(
        pg_enum(InsuranceClaimStatus, "insurance_claim_status"),
        default=InsuranceClaimStatus.PENDING,
        nullable=False,
        index=True,
    )
    invoiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
