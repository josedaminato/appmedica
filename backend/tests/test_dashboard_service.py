"""Tests del resumen de dashboard: turnos próximos sin confirmar."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    UserRole,
)
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.services.dashboard_service import DashboardService


NOW = datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
        Payment.__table__,
        HealthInsurance.__table__,
        InsuranceClaim.__table__,
    )
    for table in tables:
        table.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _org(session: Session, slug: str) -> tuple[Organization, User, Patient]:
    org = Organization(id=uuid4(), name=f"Org {slug}", slug=slug)
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email=f"{slug}@test.com",
        full_name="Owner",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Test",
        dni=slug[:20],
    )
    session.add_all([org, user, patient])
    session.flush()
    return org, user, patient


def _appt(
    org: Organization,
    patient: Patient,
    professional: User,
    *,
    start: datetime,
    status: AppointmentStatus,
) -> Appointment:
    return Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=professional.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=status,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )


def test_upcoming_unconfirmed_counts_future_pending_only(db_session: Session):
    org, user, patient = _org(db_session, "a")
    db_session.add_all(
        [
            _appt(org, patient, user, start=NOW + timedelta(hours=2), status=AppointmentStatus.PENDING),
            _appt(org, patient, user, start=NOW + timedelta(hours=3), status=AppointmentStatus.PENDING),
            _appt(org, patient, user, start=NOW + timedelta(hours=4), status=AppointmentStatus.CONFIRMED),
            _appt(org, patient, user, start=NOW - timedelta(hours=1), status=AppointmentStatus.PENDING),
        ]
    )
    db_session.commit()

    count = AppointmentRepository(db_session).count_upcoming_pending(org.id, NOW)
    assert count == 2


def test_upcoming_unconfirmed_isolates_organization(db_session: Session):
    org_a, user_a, patient_a = _org(db_session, "org-a")
    org_b, user_b, patient_b = _org(db_session, "org-b")
    db_session.add_all(
        [
            _appt(org_a, patient_a, user_a, start=NOW + timedelta(hours=1), status=AppointmentStatus.PENDING),
            _appt(org_b, patient_b, user_b, start=NOW + timedelta(hours=1), status=AppointmentStatus.PENDING),
            _appt(org_b, patient_b, user_b, start=NOW + timedelta(hours=2), status=AppointmentStatus.PENDING),
        ]
    )
    db_session.commit()

    repo = AppointmentRepository(db_session)
    assert repo.count_upcoming_pending(org_a.id, NOW) == 1
    assert repo.count_upcoming_pending(org_b.id, NOW) == 2


def test_dashboard_summary_includes_upcoming_unconfirmed(db_session: Session):
    org, user, patient = _org(db_session, "sum")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            _appt(org, patient, user, start=now + timedelta(hours=2), status=AppointmentStatus.PENDING),
            _appt(org, patient, user, start=now + timedelta(hours=3), status=AppointmentStatus.CONFIRMED),
            _appt(org, patient, user, start=now - timedelta(hours=2), status=AppointmentStatus.PENDING),
        ]
    )
    db_session.commit()

    summary = DashboardService(db_session).get_summary(org.id)
    assert summary.upcoming_unconfirmed == 1
    assert summary.unclosed_attended == 0
    assert isinstance(summary.appointments_today, int)
    assert isinstance(summary.overdue_unresolved, int)
