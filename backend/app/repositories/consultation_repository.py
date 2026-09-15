import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.consultation import Consultation
from app.models.enums import ConsultationStatus
from app.repositories.base import BaseRepository


class ConsultationRepository(BaseRepository[Consultation]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Consultation)

    def _with_relations(self, stmt):
        return stmt.options(
            joinedload(Consultation.appointment),
            joinedload(Consultation.patient),
            joinedload(Consultation.professional),
        )

    def get_by_id(
        self,
        organization_id: uuid.UUID,
        consultation_id: uuid.UUID,
    ) -> Consultation | None:
        stmt = self._with_relations(
            select(Consultation).where(
                Consultation.organization_id == organization_id,
                Consultation.id == consultation_id,
            ),
        )
        return self.db.scalars(stmt).unique().first()

    def get_by_appointment_id(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> Consultation | None:
        """Consulta primaria del turno: amends_id IS NULL."""
        stmt = self._with_relations(
            select(Consultation).where(
                Consultation.organization_id == organization_id,
                Consultation.appointment_id == appointment_id,
                Consultation.amends_id.is_(None),
            ),
        )
        return self.db.scalars(stmt).unique().first()

    def list_by_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
        include_colleague_finalized: bool = False,
        limit: int | None = None,
        finalized_only: bool = False,
    ) -> list[Consultation]:
        stmt = self._with_relations(
            select(Consultation).where(
                Consultation.organization_id == organization_id,
                Consultation.patient_id == patient_id,
            ),
        )
        if professional_id is not None:
            if include_colleague_finalized:
                stmt = stmt.where(
                    or_(
                        Consultation.professional_id == professional_id,
                        Consultation.status == ConsultationStatus.FINALIZED,
                    ),
                )
            else:
                stmt = stmt.where(Consultation.professional_id == professional_id)
        if finalized_only:
            stmt = stmt.where(Consultation.status == ConsultationStatus.FINALIZED)
        stmt = stmt.order_by(
            func.coalesce(Consultation.occurred_at, Consultation.created_at).desc(),
            Consultation.created_at.desc(),
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def exists_professional_patient(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> bool:
        stmt = (
            select(Consultation.id)
            .where(
                Consultation.organization_id == organization_id,
                Consultation.professional_id == professional_id,
                Consultation.patient_id == patient_id,
            )
            .limit(1)
        )
        return self.db.scalar(stmt) is not None

    def create(self, consultation: Consultation) -> Consultation:
        self.db.add(consultation)
        self.db.flush()
        return consultation

    def update(self, consultation: Consultation) -> Consultation:
        self.db.add(consultation)
        self.db.flush()
        return consultation
