"""Validación de pertenencia de recursos al consultorio."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import AppException
from app.core.tenant_validation import TenantResourceValidator
from app.models.appointment import Appointment
from app.models.enums import UserRole
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.services.appointment_service import AppointmentService
from app.services.patient_service import PatientService
from app.schemas.appointment import AppointmentCreate
from app.schemas.patient import PatientCreate, PatientUpdate
from datetime import datetime, timedelta, timezone
from app.models.enums import AppointmentModality, AttentionType


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    for table in (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        HealthInsurance.__table__,
        Appointment.__table__,
    ):
        table.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_orgs(session):
    org_a = Organization(id=uuid4(), name="Org A", slug="org-a")
    org_b = Organization(id=uuid4(), name="Org B", slug="org-b")
    owner_a = User(
        id=uuid4(),
        organization_id=org_a.id,
        email="owner-a@test.com",
        full_name="Owner A",
        password_hash="x",
        role=UserRole.OWNER,
    )
    prof_b = User(
        id=uuid4(),
        organization_id=org_b.id,
        email="prof-b@test.com",
        full_name="Prof B",
        password_hash="x",
        role=UserRole.PROFESSIONAL,
    )
    patient_a = Patient(
        id=uuid4(),
        organization_id=org_a.id,
        first_name="Ana",
        last_name="A",
        dni="30111111",
    )
    insurance_b = HealthInsurance(
        id=uuid4(),
        organization_id=org_b.id,
        name="OSDE B",
    )
    session.add_all([org_a, org_b, owner_a, prof_b, patient_a, insurance_b])
    session.commit()
    return org_a, org_b, owner_a, prof_b, patient_a, insurance_b


def test_validator_rejects_foreign_professional(db_session):
    org_a, org_b, _, prof_b, patient_a, _ = _seed_orgs(db_session)
    validator = TenantResourceValidator(db_session)
    with pytest.raises(AppException) as exc:
        validator.require_professional(org_a.id, prof_b.id)
    assert exc.value.status_code == 404


def test_validator_rejects_foreign_insurance(db_session):
    org_a, _, _, _, _, insurance_b = _seed_orgs(db_session)
    validator = TenantResourceValidator(db_session)
    with pytest.raises(AppException) as exc:
        validator.require_health_insurance(org_a.id, insurance_b.id)
    assert exc.value.status_code == 404


def test_create_appointment_rejects_foreign_professional(db_session):
    org_a, org_b, owner_a, prof_b, patient_a, _ = _seed_orgs(db_session)
    start = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    data = AppointmentCreate(
        patient_id=patient_a.id,
        professional_id=prof_b.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
    )
    with pytest.raises(AppException) as exc:
        AppointmentService(db_session).create_appointment(org_a.id, data, owner_a)
    assert exc.value.status_code == 404


def test_create_patient_rejects_foreign_insurance(db_session):
    org_a, _, owner_a, _, _, insurance_b = _seed_orgs(db_session)
    data = PatientCreate(
        first_name="Nuevo",
        last_name="Paciente",
        dni="30999999",
        health_insurance_id=insurance_b.id,
    )
    with pytest.raises(AppException) as exc:
        PatientService(db_session).create_patient(org_a.id, data)
    assert exc.value.status_code == 404


def test_update_patient_rejects_foreign_insurance(db_session):
    org_a, _, owner_a, _, patient_a, insurance_b = _seed_orgs(db_session)
    with pytest.raises(AppException) as exc:
        PatientService(db_session).update_patient(
            org_a.id,
            patient_a.id,
            PatientUpdate(health_insurance_id=insurance_b.id),
        )
    assert exc.value.status_code == 404
