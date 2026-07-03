import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    default_appointment_duration_minutes: Mapped[int] = mapped_column(default=30, nullable=False)
    default_private_session_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    service_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    paid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("25000"))

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    patients: Mapped[list["Patient"]] = relationship(back_populates="organization")
