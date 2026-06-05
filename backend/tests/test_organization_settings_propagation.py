from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, AttentionType, UserRole
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.services.organization_settings_propagation import (
    propagate_appointment_duration,
    propagate_private_session_amount,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            User.__table__,
            Patient.__table__,
            Appointment.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_org(session: Session) -> tuple[Organization, User, Patient]:
    org = Organization(name="Test", slug="test-org", default_appointment_duration_minutes=30)
    session.add(org)
    session.flush()
    user = User(
        organization_id=org.id,
        email="dr@test.com",
        full_name="Dr Test",
        role=UserRole.OWNER,
        password_hash="x",
    )
    patient = Patient(
        organization_id=org.id,
        first_name="Ana",
        last_name="Test",
        dni="12345678",
    )
    session.add_all([user, patient])
    session.flush()
    return org, user, patient


def _future_appt(
    session: Session,
    org: Organization,
    user: User,
    patient: Patient,
    *,
    amount: Decimal | None,
    duration_min: int = 30,
    attention: AttentionType = AttentionType.PRIVATE,
) -> Appointment:
    start = datetime.now(timezone.utc) + timedelta(days=2)
    appt = Appointment(
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=user.id,
        start_at=start,
        end_at=start + timedelta(minutes=duration_min),
        status=AppointmentStatus.CONFIRMED,
        attention_type=attention,
        expected_amount=amount,
    )
    session.add(appt)
    session.commit()
    return appt


def test_propagate_amount_on_inflation(db_session: Session):
    org, user, patient = _seed_org(db_session)
    _future_appt(db_session, org, user, patient, amount=Decimal("15000"))
    _future_appt(db_session, org, user, patient, amount=Decimal("18000"))
    _future_appt(db_session, org, user, patient, amount=None)

    n = propagate_private_session_amount(
        db_session, org.id, Decimal("15000"), Decimal("20000")
    )
    db_session.commit()

    assert n == 2
    appts = db_session.query(Appointment).order_by(Appointment.expected_amount).all()
    amounts = sorted(
        [a.expected_amount for a in appts if a.expected_amount is not None],
        key=lambda x: x,
    )
    assert amounts == [Decimal("18000"), Decimal("20000"), Decimal("20000")]


def test_propagate_duration(db_session: Session):
    org, user, patient = _seed_org(db_session)
    _future_appt(db_session, org, user, patient, amount=None, duration_min=30)
    _future_appt(db_session, org, user, patient, amount=None, duration_min=60)

    n = propagate_appointment_duration(db_session, org.id, 30, 45)
    db_session.commit()

    assert n == 1
    appts = db_session.query(Appointment).all()
    mins = sorted(
        int((a.end_at - a.start_at).total_seconds() // 60) for a in appts
    )
    assert mins == [45, 60]
