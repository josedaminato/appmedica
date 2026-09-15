"""RBAC de GET /reminders y POST /reminders/appointments/{id}/schedule."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(_element, _compiler, **_kw):
    return "JSON"

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    ReminderChannel,
    ReminderKind,
    ReminderStatus,
    UserRole,
)
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.reminder import ReminderJob
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
        ReminderJob.__table__,
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
def seeded(db_session: Session):
    now = datetime.now(timezone.utc)
    org = Organization(id=uuid4(), name="Clínica Reminders", slug="clinica-reminders")
    password = "TestPass123!"
    owner = User(
        id=uuid4(), organization_id=org.id, email="owner-rem@example.com",
        full_name="Owner Rem", password_hash=hash_password(password), role=UserRole.OWNER,
    )
    staff = User(
        id=uuid4(), organization_id=org.id, email="staff-rem@example.com",
        full_name="Staff Rem", password_hash=hash_password(password), role=UserRole.STAFF,
    )
    prof_a = User(
        id=uuid4(), organization_id=org.id, email="profa-rem@example.com",
        full_name="Prof A Rem", password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(), organization_id=org.id, email="profb-rem@example.com",
        full_name="Prof B Rem", password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    org2 = Organization(id=uuid4(), name="Otra Rem", slug="otra-reminders")
    owner2 = User(
        id=uuid4(), organization_id=org2.id, email="owner2-rem@example.com",
        full_name="Owner 2", password_hash=hash_password(password), role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(), organization_id=org.id, first_name="Ana", last_name="Rem",
        dni="50000001", phone="2615550001",
    )
    start_a = now + timedelta(days=5)
    start_b = now + timedelta(days=6)
    appt_a = Appointment(
        id=uuid4(), organization_id=org.id, patient_id=patient.id,
        professional_id=prof_a.id, start_at=start_a, end_at=start_a + timedelta(minutes=30),
        status=AppointmentStatus.PENDING, modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE, closure_status=AppointmentClosureStatus.NONE,
    )
    appt_b = Appointment(
        id=uuid4(), organization_id=org.id, patient_id=patient.id,
        professional_id=prof_b.id, start_at=start_b, end_at=start_b + timedelta(minutes=30),
        status=AppointmentStatus.PENDING, modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE, closure_status=AppointmentClosureStatus.NONE,
    )
    job_a = ReminderJob(
        id=uuid4(), organization_id=org.id, appointment_id=appt_a.id, patient_id=patient.id,
        kind=ReminderKind.APPOINTMENT_REMINDER_24H, channel=ReminderChannel.EMAIL,
        status=ReminderStatus.SCHEDULED, scheduled_at=now, next_attempt_at=now, attempt_count=0,
    )
    job_b = ReminderJob(
        id=uuid4(), organization_id=org.id, appointment_id=appt_b.id, patient_id=patient.id,
        kind=ReminderKind.APPOINTMENT_REMINDER_24H, channel=ReminderChannel.EMAIL,
        status=ReminderStatus.SCHEDULED, scheduled_at=now + timedelta(minutes=1),
        next_attempt_at=now + timedelta(minutes=1), attempt_count=0,
    )
    db_session.add_all([
        org, owner, staff, prof_a, prof_b, org2, owner2, patient, appt_a, appt_b, job_a, job_b,
    ])
    db_session.commit()
    return {
        "org": org, "org2": org2, "owner": owner, "staff": staff,
        "prof_a": prof_a, "prof_b": prof_b, "owner2": owner2,
        "appt_a": appt_a, "appt_b": appt_b, "job_a": job_a, "job_b": job_b,
        "password": password,
    }


@pytest.fixture()
def api_client(db_session: Session, seeded, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    previous = limiter.enabled
    limiter.enabled = False

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, seeded
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        limiter.enabled = previous


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_owner_lists_organization_reminders(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["owner"].email, clinic["password"])
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(clinic["job_a"].id) in ids
    assert str(clinic["job_b"].id) in ids


def test_staff_lists_organization_reminders(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["staff"].email, clinic["password"])
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(clinic["job_a"].id) in ids
    assert str(clinic["job_b"].id) in ids


def test_professional_lists_only_own_appointment_reminders(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["prof_a"].email, clinic["password"])
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(clinic["job_a"].id) in ids
    assert str(clinic["job_b"].id) not in ids


def test_professional_cannot_list_colleague_reminders(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["prof_b"].email, clinic["password"])
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(clinic["job_b"].id) in ids
    assert str(clinic["job_a"].id) not in ids


def test_reminders_do_not_cross_organizations(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["owner2"].email, clinic["password"])
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()}
    assert str(clinic["job_a"].id) not in ids
    assert str(clinic["job_b"].id) not in ids


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_owner_can_schedule_any_org_appointment(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["owner"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{clinic['appt_b'].id}/schedule",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    mock_schedule.assert_called_once()


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_staff_can_schedule_any_org_appointment(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["staff"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{clinic['appt_a'].id}/schedule",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    mock_schedule.assert_called_once()


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_professional_can_schedule_own_appointment(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["prof_a"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{clinic['appt_a'].id}/schedule",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    mock_schedule.assert_called_once()


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_professional_cannot_schedule_colleague_appointment(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["prof_a"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{clinic['appt_b'].id}/schedule",
        headers=headers,
    )
    assert resp.status_code == 403, resp.text
    mock_schedule.assert_not_called()


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_schedule_foreign_org_appointment_is_not_found(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["owner2"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{clinic['appt_a'].id}/schedule",
        headers=headers,
    )
    assert resp.status_code == 404, resp.text
    mock_schedule.assert_not_called()


@patch("app.api.v1.endpoints.reminders.ReminderService.schedule_for_appointment")
def test_schedule_unknown_appointment_is_not_found(mock_schedule, api_client):
    mock_schedule.return_value = []
    client, clinic = api_client
    headers = _login(client, clinic["owner"].email, clinic["password"])
    resp = client.post(
        f"/api/v1/reminders/appointments/{uuid4()}/schedule",
        headers=headers,
    )
    assert resp.status_code == 404, resp.text
    mock_schedule.assert_not_called()
