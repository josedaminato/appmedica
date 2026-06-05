import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.enums import ReminderStatus
from app.models.reminder import ReminderJob
from app.repositories.base import BaseRepository


class ReminderRepository(BaseRepository[ReminderJob]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ReminderJob)

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ReminderJob]:
        stmt = (
            select(ReminderJob)
            .where(ReminderJob.organization_id == organization_id)
            .order_by(ReminderJob.scheduled_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_due(
        self,
        *,
        before: datetime,
        organization_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ReminderJob]:
        conditions = [
            ReminderJob.status == ReminderStatus.SCHEDULED,
            ReminderJob.scheduled_at <= before,
        ]
        if organization_id is not None:
            conditions.append(ReminderJob.organization_id == organization_id)

        stmt = (
            select(ReminderJob)
            .where(*conditions)
            .order_by(ReminderJob.scheduled_at.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, job: ReminderJob) -> ReminderJob:
        self.db.add(job)
        self.db.flush()
        return job

    def cancel_scheduled_for_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> int:
        appt_key = str(appointment_id)
        stmt = (
            update(ReminderJob)
            .where(
                ReminderJob.organization_id == organization_id,
                ReminderJob.status == ReminderStatus.SCHEDULED,
                ReminderJob.payload["appointment_id"].astext == appt_key,
            )
            .values(status=ReminderStatus.CANCELLED)
        )
        result = self.db.execute(stmt)
        return result.rowcount or 0
