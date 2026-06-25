"""Protección contra doble cierre de turno."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AppException
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    UserRole,
)
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.user import User
from app.schemas.appointment import CloseAppointmentRequest
from app.services.appointment_closure_service import AppointmentClosureService


def _make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_attended(engine):
    tables = (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
        Payment.__table__,
        HealthInsurance.__table__,
    )
    for table in tables:
        table.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    org = Organization(id=uuid4(), name="Clinic", slug="clinic")
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@clinic.test",
        full_name="Owner",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Test",
        dni="30123456",
    )
    start = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
    appt = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=user.id,
        start_at=start,
        end_at=datetime(2026, 6, 10, 10, 30, tzinfo=timezone.utc),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
        expected_amount=Decimal("5000"),
    )
    session.add_all([org, user, patient, appt])
    session.commit()
    session.close()
    return org.id, user, appt.id, SessionLocal


def test_double_close_second_attempt_fails():
    engine = _make_engine()
    org_id, user, appt_id, SessionLocal = _seed_attended(engine)

    session = SessionLocal()
    service = AppointmentClosureService(session)
    service.close_appointment(
        org_id,
        appt_id,
        CloseAppointmentRequest(closure_type=AppointmentClosureStatus.PAID, amount=Decimal("5000"), method="cash"),
        user,
    )
    session.close()

    session2 = SessionLocal()
    with pytest.raises(AppException) as exc:
        AppointmentClosureService(session2).close_appointment(
            org_id,
            appt_id,
            CloseAppointmentRequest(closure_type=AppointmentClosureStatus.PAID, amount=Decimal("5000"), method="cash"),
            user,
        )
    assert exc.value.status_code == 400
    assert "cerrado" in exc.value.detail["message"].lower()  # type: ignore[index]
    session2.close()


def test_close_uses_row_lock_and_leaves_single_closure_state():
    """Simula doble intento: el segundo falla y el turno queda cerrado una sola vez."""
    engine = _make_engine()
    org_id, user, appt_id, SessionLocal = _seed_attended(engine)
    request = CloseAppointmentRequest(
        closure_type=AppointmentClosureStatus.PENDING,
        amount=Decimal("8000"),
        method="cash",
    )

    s1 = SessionLocal()
    AppointmentClosureService(s1).close_appointment(org_id, appt_id, request, user)
    s1.close()

    s2 = SessionLocal()
    with pytest.raises(AppException):
        AppointmentClosureService(s2).close_appointment(org_id, appt_id, request, user)
    s2.close()

    verify = SessionLocal()
    appt = verify.get(Appointment, appt_id)
    assert appt.closure_status == AppointmentClosureStatus.PENDING
    payment_count = verify.scalar(
        select(func.count()).select_from(Payment).where(Payment.appointment_id == appt_id),
    )
    assert payment_count == 1
    verify.close()
