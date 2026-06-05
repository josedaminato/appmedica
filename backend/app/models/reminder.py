import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from app.db.enums import pg_enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReminderChannel, ReminderStatus


class ReminderJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Jobs de recordatorios por turno (email / WhatsApp)."""

    __tablename__ = "reminder_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[ReminderChannel] = mapped_column(
        pg_enum(ReminderChannel, "reminder_channel"),
        nullable=False,
    )
    status: Mapped[ReminderStatus] = mapped_column(
        pg_enum(ReminderStatus, "reminder_status"),
        default=ReminderStatus.SCHEDULED,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
