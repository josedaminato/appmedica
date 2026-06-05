import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.appointment import Appointment
from app.models.enums import AppointmentClosureStatus, AppointmentStatus
from app.models.patient import Patient
from app.models.user import User
from app.repositories.base import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Appointment)

    def _with_relations(self, stmt):
        return stmt.options(
            joinedload(Appointment.patient),
            joinedload(Appointment.professional),
            joinedload(Appointment.health_insurance),
        )

    def get_by_id(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment | None:
        stmt = self._with_relations(
            select(Appointment).where(
                Appointment.organization_id == organization_id,
                Appointment.id == appointment_id,
            ),
        )
        return self.db.scalars(stmt).unique().first()

    def list_in_range(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        professional_id: uuid.UUID | None = None,
        status: AppointmentStatus | None = None,
        patient_q: str | None = None,
        closure_status: AppointmentClosureStatus | None = None,
        use_date_filter: bool = False,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Appointment]:
        conditions = [
            Appointment.organization_id == organization_id,
            Appointment.status != AppointmentStatus.RESCHEDULED,
        ]
        if use_date_filter and start_date and end_date:
            conditions.append(cast(Appointment.start_at, Date) >= start_date)
            conditions.append(cast(Appointment.start_at, Date) < end_date)
        else:
            conditions.append(Appointment.start_at >= start)
            conditions.append(Appointment.start_at < end)

        stmt = self._with_relations(select(Appointment).where(*conditions))
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if closure_status:
            stmt = stmt.where(Appointment.closure_status == closure_status)
        if patient_q:
            term = f"%{patient_q.strip().lower()}%"
            stmt = stmt.join(Patient).where(
                or_(
                    func.lower(Patient.first_name).like(term),
                    func.lower(Patient.last_name).like(term),
                    func.lower(Patient.dni).like(term),
                ),
            )
        stmt = stmt.order_by(Appointment.start_at.asc())
        return list(self.db.scalars(stmt).unique().all())

    def find_overlapping(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None,
        start_at: datetime,
        end_at: datetime,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> list[Appointment]:
        if not professional_id:
            return []

        blocking = (
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.ATTENDED,
        )
        stmt = self._with_relations(
            select(Appointment).where(
                Appointment.organization_id == organization_id,
                Appointment.professional_id == professional_id,
                Appointment.status.in_(blocking),
                Appointment.start_at < end_at,
                Appointment.end_at > start_at,
            ),
        )
        if exclude_appointment_id:
            stmt = stmt.where(Appointment.id != exclude_appointment_id)
        return list(self.db.scalars(stmt).unique().all())

    def list_for_calendar_feed(
        self,
        organization_id: uuid.UUID,
        *,
        start_date: date,
        end_date_exclusive: date,
        professional_id: uuid.UUID | None = None,
    ) -> list[Appointment]:
        excluded = (
            AppointmentStatus.CANCELLED,
            AppointmentStatus.RESCHEDULED,
            AppointmentStatus.NO_SHOW,
        )
        conditions = [
            Appointment.organization_id == organization_id,
            Appointment.status.not_in(excluded),
            cast(Appointment.start_at, Date) >= start_date,
            cast(Appointment.start_at, Date) < end_date_exclusive,
        ]
        stmt = self._with_relations(select(Appointment).where(*conditions))
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        stmt = stmt.order_by(Appointment.start_at.asc())
        return list(self.db.scalars(stmt).unique().all())

    def count_today(self, organization_id: uuid.UUID, day: date) -> int:
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == organization_id,
            Appointment.start_at >= start,
            Appointment.start_at < end,
            Appointment.status.not_in(
                [AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED],
            ),
        )
        return self.db.scalar(stmt) or 0

    def count_unclosed_attended(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == organization_id,
            Appointment.status == AppointmentStatus.ATTENDED,
            Appointment.closure_status == AppointmentClosureStatus.NONE,
        )
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        return self.db.scalar(stmt) or 0

    def count_overdue_unresolved(
        self,
        organization_id: uuid.UUID,
        now: datetime,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == organization_id,
            Appointment.end_at < now,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
        )
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        return self.db.scalar(stmt) or 0

    def list_upcoming(self, organization_id: uuid.UUID, now: datetime, limit: int = 5) -> list[Appointment]:
        stmt = self._with_relations(
            select(Appointment)
            .where(
                Appointment.organization_id == organization_id,
                Appointment.start_at >= now,
                Appointment.status.in_(
                    [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
                ),
            )
            .order_by(Appointment.start_at.asc())
            .limit(limit),
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_unclosed_attended(self, organization_id: uuid.UUID, limit: int = 10) -> list[Appointment]:
        stmt = self._with_relations(
            select(Appointment)
            .where(
                Appointment.organization_id == organization_id,
                Appointment.status == AppointmentStatus.ATTENDED,
                Appointment.closure_status == AppointmentClosureStatus.NONE,
            )
            .order_by(Appointment.start_at.desc())
            .limit(limit),
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_by_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        *,
        upcoming_only: bool = False,
        limit: int = 10,
    ) -> list[Appointment]:
        now = datetime.now(timezone.utc)
        stmt = self._with_relations(
            select(Appointment).where(
                Appointment.organization_id == organization_id,
                Appointment.patient_id == patient_id,
                Appointment.status != AppointmentStatus.RESCHEDULED,
            ),
        )
        if upcoming_only:
            stmt = stmt.where(
                Appointment.start_at >= now,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            ).order_by(Appointment.start_at.asc())
        else:
            stmt = stmt.order_by(Appointment.start_at.desc())
        stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def count_no_shows(self, organization_id: uuid.UUID, patient_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == organization_id,
            Appointment.status == AppointmentStatus.NO_SHOW,
        )
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        return self.db.scalar(stmt) or 0

    def count_no_shows_since(
        self,
        organization_id: uuid.UUID,
        since: datetime,
        patient_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == organization_id,
            Appointment.status == AppointmentStatus.NO_SHOW,
            Appointment.start_at >= since,
        )
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        return self.db.scalar(stmt) or 0

    def count_in_date_range(
        self,
        organization_id: uuid.UUID,
        start_date: date,
        end_date_exclusive: date,
        *,
        status: AppointmentStatus | None = None,
    ) -> int:
        conditions = [
            Appointment.organization_id == organization_id,
            cast(Appointment.start_at, Date) >= start_date,
            cast(Appointment.start_at, Date) < end_date_exclusive,
            Appointment.status != AppointmentStatus.RESCHEDULED,
        ]
        if status is not None:
            conditions.append(Appointment.status == status)
        stmt = select(func.count()).select_from(Appointment).where(*conditions)
        return self.db.scalar(stmt) or 0

    def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def update(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment
