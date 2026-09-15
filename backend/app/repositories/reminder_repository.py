import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import ReminderStatus
from app.models.reminder import ReminderJob
from app.repositories.base import BaseRepository

ORPHAN_SENDING_AFTER = timedelta(minutes=10)


class ReminderRepository(BaseRepository[ReminderJob]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ReminderJob)

    def _supports_skip_locked(self) -> bool:
        bind = self.db.get_bind()
        return bind.dialect.name == "postgresql"

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ReminderJob]:
        stmt = select(ReminderJob).where(ReminderJob.organization_id == organization_id)
        if professional_id is not None:
            stmt = stmt.join(
                Appointment,
                ReminderJob.appointment_id == Appointment.id,
            ).where(
                Appointment.organization_id == organization_id,
                Appointment.professional_id == professional_id,
            )
        stmt = stmt.order_by(ReminderJob.scheduled_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def recover_orphan_sending(
        self,
        *,
        before: datetime,
        organization_id: uuid.UUID | None = None,
    ) -> int:
        """Devuelve a scheduled los jobs sending huérfanos (proceso caído)."""
        cutoff = before - ORPHAN_SENDING_AFTER
        conditions = [
            ReminderJob.status == ReminderStatus.SENDING,
            ReminderJob.updated_at <= cutoff,
        ]
        if organization_id is not None:
            conditions.append(ReminderJob.organization_id == organization_id)
        stmt = (
            update(ReminderJob)
            .where(*conditions)
            .values(
                status=ReminderStatus.SCHEDULED,
                error_code="orphan_sending",
                error_message="Recovered after worker crash",
                updated_at=before,
            )
        )
        result = self.db.execute(stmt)
        return result.rowcount or 0

    def lock_due_job(
        self,
        *,
        before: datetime,
        organization_id: uuid.UUID | None = None,
    ) -> ReminderJob | None:
        """Toma un job due. En PostgreSQL usa FOR UPDATE SKIP LOCKED."""
        conditions = [
            ReminderJob.status == ReminderStatus.SCHEDULED,
            ReminderJob.next_attempt_at <= before,
        ]
        if organization_id is not None:
            conditions.append(ReminderJob.organization_id == organization_id)

        stmt = (
            select(ReminderJob)
            .where(*conditions)
            .order_by(ReminderJob.next_attempt_at.asc())
            .limit(1)
        )
        if self._supports_skip_locked():
            stmt = stmt.with_for_update(skip_locked=True)
        return self.db.scalars(stmt).first()

    def create(self, job: ReminderJob) -> ReminderJob:
        self.db.add(job)
        self.db.flush()
        return job

    def update_if_sending(self, job_id: uuid.UUID, values: dict) -> bool:
        """Aplica el resultado solo si el job sigue en sending. Evita cancelled → sent."""
        stmt = (
            update(ReminderJob)
            .where(
                ReminderJob.id == job_id,
                ReminderJob.status == ReminderStatus.SENDING,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        result = self.db.execute(stmt)
        return (result.rowcount or 0) == 1

    def cancel_scheduled_for_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> int:
        stmt = (
            update(ReminderJob)
            .where(
                ReminderJob.organization_id == organization_id,
                ReminderJob.appointment_id == appointment_id,
                ReminderJob.status.in_((ReminderStatus.SCHEDULED, ReminderStatus.SENDING)),
            )
            .values(status=ReminderStatus.CANCELLED, error_code="appointment_cancelled")
        )
        result = self.db.execute(stmt)
        return result.rowcount or 0
