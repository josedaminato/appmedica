import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import pg_enum
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReminderChannel, ReminderKind, ReminderStatus


class ReminderJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Intención de envío de un recordatorio. El turno sigue siendo la fuente de verdad."""

    __tablename__ = "reminder_jobs"
    __table_args__ = (
        Index("ix_reminder_jobs_appointment_id", "appointment_id"),
        Index("ix_reminder_jobs_status_next_attempt_at", "status", "next_attempt_at"),
        Index(
            "uq_reminder_jobs_active_appointment_kind_channel",
            "appointment_id",
            "kind",
            "channel",
            unique=True,
            postgresql_where=text("status IN ('scheduled', 'sending', 'sent')"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # El turno es la fuente de verdad de fecha, estado y paciente.
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[ReminderKind] = mapped_column(
        pg_enum(ReminderKind, "reminder_kind"),
        default=ReminderKind.APPOINTMENT_REMINDER_24H,
        nullable=False,
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
    # Próximo intento (igual a scheduled_at en el alta; se mueve en retries).
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Nombre corto del adapter (smtp, twilio, meta). No hay provider_message_id aún.
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
