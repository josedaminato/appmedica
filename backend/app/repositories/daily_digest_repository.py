import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_digest_log import DailyDigestLog
from app.repositories.base import BaseRepository


class DailyDigestRepository(BaseRepository[DailyDigestLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, DailyDigestLog)

    def was_sent(self, user_id: uuid.UUID, target_date: date) -> bool:
        stmt = select(DailyDigestLog.id).where(
            DailyDigestLog.user_id == user_id,
            DailyDigestLog.target_date == target_date,
        )
        return self.db.scalar(stmt) is not None

    def mark_sent(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        target_date: date,
    ) -> DailyDigestLog:
        row = DailyDigestLog(
            organization_id=organization_id,
            user_id=user_id,
            target_date=target_date,
        )
        self.db.add(row)
        self.db.flush()
        return row
