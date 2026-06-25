"""Validación de que los recursos referenciados pertenecen al consultorio."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.repositories.health_insurance_repository import HealthInsuranceRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository


class TenantResourceValidator:
    def __init__(self, db: Session) -> None:
        self.patients = PatientRepository(db)
        self.users = UserRepository(db)
        self.insurances = HealthInsuranceRepository(db)

    def require_patient(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        if not self.patients.get_by_id(organization_id, patient_id):
            raise not_found("Paciente")

    def require_professional(self, organization_id: uuid.UUID, professional_id: uuid.UUID) -> None:
        user = self.users.get_by_id_in_organization(organization_id, professional_id)
        if not user or not user.is_active:
            raise not_found("Profesional")

    def require_health_insurance(self, organization_id: uuid.UUID, insurance_id: uuid.UUID) -> None:
        if not self.insurances.get_by_id(organization_id, insurance_id):
            raise not_found("Obra social")
