"""Protección transaccional contra doble reserva."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AppException
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    UserRole,
)
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import AppointmentService


def _make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed(engine):
    tables = (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
        HealthInsurance.__table__,
    )
    for table in tables:
        table.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    org = Organization(id=uuid4(), name="Clinic", slug="clinic")
    owner = User(
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
    session.add_all([org, owner, patient])
    session.commit()
    session.close()
    return org.id, owner, patient.id, SessionLocal


def _appointment_payload(patient_id, professional_id):
    start = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)
    return AppointmentCreate(
        patient_id=patient_id,
        professional_id=professional_id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
    )


def test_second_booking_same_slot_rejected():
    engine = _make_engine()
    org_id, owner, patient_id, SessionLocal = _seed(engine)
    data = _appointment_payload(patient_id, owner.id)

    session1 = SessionLocal()
    with patch("app.services.appointment_service.ReminderService") as mock_rem:
        mock_rem.return_value.schedule_for_appointment.return_value = None
        AppointmentService(session1).create_appointment(org_id, data, owner)
    session1.close()

    session2 = SessionLocal()
    with patch("app.services.appointment_service.ReminderService") as mock_rem:
        mock_rem.return_value.schedule_for_appointment.return_value = None
        with pytest.raises(AppException) as exc:
            AppointmentService(session2).create_appointment(org_id, data, owner)
    assert exc.value.status_code == 409
    session2.close()

    verify = SessionLocal()
    count = verify.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.organization_id == org_id,
            Appointment.professional_id == owner.id,
            Appointment.status != AppointmentStatus.RESCHEDULED,
        ),
    )
    assert count == 1
    verify.close()


def test_concurrent_booking_same_slot_only_one_created():
    """Dos hilos compiten por el mismo horario; FOR UPDATE serializa en PostgreSQL."""
    import threading

    engine = _make_engine()
    if engine.dialect.name == "sqlite":
        pytest.skip("SQLite en tests no garantiza serialización entre hilos; ver test_second_booking_same_slot_rejected")

    org_id, owner, patient_id, SessionLocal = _seed(engine)
    data = _appointment_payload(patient_id, owner.id)

    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def book():
        session = SessionLocal()
        try:
            barrier.wait()
            with patch("app.services.appointment_service.ReminderService") as mock_rem:
                mock_rem.return_value.schedule_for_appointment.return_value = None
                AppointmentService(session).create_appointment(org_id, data, owner)
            with lock:
                results.append("ok")
        except AppException:
            with lock:
                results.append("conflict")
        except Exception:
            with lock:
                results.append("error")
        finally:
            session.close()

    t1 = threading.Thread(target=book)
    t2 = threading.Thread(target=book)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    verify = SessionLocal()
    count = verify.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.organization_id == org_id,
            Appointment.professional_id == owner.id,
            Appointment.status != AppointmentStatus.RESCHEDULED,
        ),
    )
    verify.close()

    assert count == 1
    assert results.count("ok") >= 1
