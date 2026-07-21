"""Turnos fijos semanales (serie)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        HealthInsurance.__table__,
        Appointment.__table__,
    ):
        table.create(engine, checkfirst=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(db_session: Session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REGISTRATION_ENABLED", "true")
    get_settings.cache_clear()

    org = Organization(id=uuid4(), name="Consultorio Fijo", slug="consultorio-fijo")
    password = "TestPass123!"
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="fijo@example.com",
        full_name="Dra Fija",
        password_hash=hash_password(password),
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Pérez",
        dni="30111222",
    )
    db_session.add_all([org, owner, patient])
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, {
            "org": org,
            "owner": owner,
            "patient": patient,
            "email": owner.email,
            "password": password,
        }
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _login(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@patch("app.services.appointment_service.ReminderService")
def test_create_weekly_fixed_appointments(mock_reminder_cls, api_client, db_session: Session):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["email"], clinic["password"])
    start = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)  # lunes

    resp = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": str(clinic["patient"].id),
            "professional_id": str(clinic["owner"].id),
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(minutes=50)).isoformat(),
            "modality": "presencial",
            "attention_type": "private",
            "expected_amount": "15000",
            "recurring_weekly": True,
            "weeks": 4,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created_count"] == 4
    assert body["series_id"] is not None
    assert len(body["appointments"]) == 4

    starts = [datetime.fromisoformat(a["start_at"].replace("Z", "+00:00")) for a in body["appointments"]]
    assert starts[1] - starts[0] == timedelta(days=7)
    assert starts[3] - starts[0] == timedelta(days=21)
    assert all(a["series_id"] == body["series_id"] for a in body["appointments"])

    from uuid import UUID

    rows = db_session.scalars(
        select(Appointment).where(Appointment.series_id == UUID(body["series_id"])),
    ).all()
    assert len(rows) == 4


@patch("app.services.appointment_service.ReminderService")
def test_cancel_series_from_midpoint(mock_reminder_cls, api_client, db_session: Session):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    mock_reminder_cls.return_value.cancel_for_appointment.return_value = None
    headers = _login(client, clinic["email"], clinic["password"])
    start = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)

    create = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": str(clinic["patient"].id),
            "professional_id": str(clinic["owner"].id),
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(minutes=50)).isoformat(),
            "modality": "presencial",
            "attention_type": "private",
            "recurring_weekly": True,
            "weeks": 4,
        },
    )
    assert create.status_code == 201, create.text
    second_id = create.json()["appointments"][1]["id"]
    series_id = create.json()["series_id"]

    cancel = client.post(f"/api/v1/appointments/{second_id}/cancel-series", headers=headers)
    assert cancel.status_code == 200, cancel.text
    assert "3" in cancel.json()["message"]

    from uuid import UUID

    rows = db_session.scalars(
        select(Appointment)
        .where(Appointment.series_id == UUID(series_id))
        .order_by(Appointment.start_at),
    ).all()
    assert rows[0].status == AppointmentStatus.PENDING
    assert rows[1].status == AppointmentStatus.CANCELLED
    assert rows[2].status == AppointmentStatus.CANCELLED
    assert rows[3].status == AppointmentStatus.CANCELLED
