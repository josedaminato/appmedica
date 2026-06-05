import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DailyDigestLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Evita enviar dos veces el mismo resumen diario a un usuario."""

    __tablename__ = "daily_digest_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "target_date", name="uq_daily_digest_user_date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
