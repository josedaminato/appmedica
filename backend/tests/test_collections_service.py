"""Tests básicos del módulo de cobros/deuda."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.payment import Payment
from app.models.user import User
from app.services.collections_service import CollectionsService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    for table in (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
        Payment.__table__,
        HealthInsurance.__table__,
        InsuranceClaim.__table__,
    ):
        table.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_private_debt(session: Session):
    org = Organization(id=uuid4(), name="Test", slug="test")
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email="t@test.com",
        full_name="Dr Test",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Lopez",
        dni="30111222",
    )
    session.add_all([org, user, patient])
    session.flush()
    start = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
    appt = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=user.id,
        start_at=start,
        end_at=datetime(2026, 5, 20, 10, 30, tzinfo=timezone.utc),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.PENDING,
        expected_amount=Decimal("5000"),
    )
    session.add(appt)
    session.add(
        Payment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient.id,
            appointment_id=appt.id,
            professional_id=user.id,
            amount=Decimal("5000"),
            method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING,
        ),
    )
    session.commit()
    return org.id


def test_summary_private_debt(db_session: Session):
    org_id = _seed_private_debt(db_session)
    summary = CollectionsService(db_session).get_summary(org_id)
    assert summary.private_debt_total == Decimal("5000")
    assert summary.unclosed_attended >= 0


def test_list_private_tab(db_session: Session):
    org_id = _seed_private_debt(db_session)
    rows = CollectionsService(db_session).list_items(org_id, "private")
    assert len(rows) == 1
    assert rows[0].balance_pending == Decimal("5000")
    assert rows[0].can_collect is True
