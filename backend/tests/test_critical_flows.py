"""Flujos críticos end-to-end para detectar regresiones pre-deploy."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
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
        Appointment.__table__,
        Payment.__table__,
        HealthInsurance.__table__,
        InsuranceClaim.__table__,
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
def seeded_clinic(db_session: Session):
    org = Organization(id=uuid4(), name="Clínica Crítica", slug="clinica-critica")
    password = "TestPass123!"
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@example.com",
        full_name="Dr Owner",
        password_hash=hash_password(password),
        role=UserRole.OWNER,
    )
    db_session.add_all([org, owner])
    db_session.commit()
    return {
        "org": org,
        "owner": owner,
        "email": owner.email,
        "password": password,
    }


@pytest.fixture()
def api_client(db_session: Session, seeded_clinic, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REGISTRATION_ENABLED", "true")
    get_settings.cache_clear()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, seeded_clinic
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@patch("app.services.appointment_service.ReminderService")
def test_critical_clinic_flow(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    mock_reminder_cls.return_value.cancel_for_appointment.return_value = None

    login = client.post(
        "/api/v1/auth/login",
        json={"email": clinic["email"], "password": clinic["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patient_resp = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "first_name": "María",
            "last_name": "García",
            "dni": "27123456",
            "phone": "2615550000",
        },
    )
    assert patient_resp.status_code == 201, patient_resp.text
    patient_id = patient_resp.json()["id"]

    start = datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc)
    appt_resp = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "professional_id": str(clinic["owner"].id),
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(minutes=30)).isoformat(),
            "modality": "presencial",
            "attention_type": "private",
            "expected_amount": "10000",
        },
    )
    assert appt_resp.status_code == 201, appt_resp.text
    appt_id = appt_resp.json()["appointments"][0]["id"]

    attend = client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    assert attend.status_code == 200, attend.text
    assert attend.json()["status"] == "attended"

    close = client.post(
        f"/api/v1/appointments/{appt_id}/close",
        headers=headers,
        json={
            "closure_type": "partial",
            "amount": "10000",
            "paid_amount": "4000",
            "method": "cash",
        },
    )
    assert close.status_code == 200, close.text
    assert close.json()["closure_status"] == "partial"

    pay = client.post(
        f"/api/v1/appointments/{appt_id}/payments",
        headers=headers,
        json={"amount": "2000", "method": "transfer"},
    )
    assert pay.status_code == 200, pay.text

    debt = client.get("/api/v1/payments/items?tab=private", headers=headers)
    assert debt.status_code == 200, debt.text
    assert len(debt.json()) >= 1
    assert any(float(row["balance_pending"]) > 0 for row in debt.json())

    alerts = client.get("/api/v1/dashboard/alerts", headers=headers)
    assert alerts.status_code == 200, alerts.text
    body = alerts.json()
    assert "top_debt_patients" in body
    assert "partial_payments_pending" in body

    summary = client.get("/api/v1/payments/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert float(summary.json()["private_debt_total"]) > 0


def test_login_rejects_bad_password(api_client):
    client, clinic = api_client
    response = client.post(
        "/api/v1/auth/login",
        json={"email": clinic["email"], "password": "WrongPass99!"},
    )
    assert response.status_code == 401
