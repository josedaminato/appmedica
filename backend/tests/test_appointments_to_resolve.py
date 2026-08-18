"""GET /appointments/to-resolve: lista de sin cerrar y vencidos, todas las fechas."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    UserRole,
)
from app.models.health_insurance import HealthInsurance
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
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    previous_limiter_enabled = limiter.enabled
    limiter.enabled = False

    org = Organization(id=uuid4(), name="Clínica Resolver", slug="clinica-resolver")
    password = "TestPass123!"
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner-resolver@example.com",
        full_name="Dr Owner",
        password_hash=hash_password(password),
        role=UserRole.OWNER,
    )
    prof_a = User(
        id=uuid4(),
        organization_id=org.id,
        email="profa-resolver@example.com",
        full_name="Dr Prof A",
        password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(),
        organization_id=org.id,
        email="profb-resolver@example.com",
        full_name="Dr Prof B",
        password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    db_session.add_all([org, owner, prof_a, prof_b])
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, {
            "org": org,
            "owner": owner,
            "prof_a": prof_a,
            "prof_b": prof_b,
            "password": password,
        }
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        limiter.enabled = previous_limiter_enabled


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_patient(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "first_name": "María",
            "last_name": "García",
            "dni": f"{uuid4().int % 10_000_000:08d}",
            "phone": "2615550000",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_appointment(
    client: TestClient,
    headers: dict,
    *,
    patient_id: str,
    professional_id: str,
    start: datetime,
) -> str:
    resp = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(minutes=30)).isoformat(),
            "modality": "presencial",
            "attention_type": "private",
            "expected_amount": "10000",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["appointments"][0]["id"]


def _ids(resp) -> set[str]:
    assert resp.status_code == 200, resp.text
    return {row["id"] for row in resp.json()}


@patch("app.services.appointment_service.ReminderService")
def test_unclosed_includes_yesterday(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=yesterday,
    )
    attend = client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    assert attend.status_code == 200, attend.text

    listed = client.get("/api/v1/appointments/to-resolve?kind=unclosed", headers=headers)
    assert appt_id in _ids(listed)


@patch("app.services.appointment_service.ReminderService")
def test_unclosed_excludes_paid_and_closed(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime.now(timezone.utc) - timedelta(days=1)

    paid_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )
    closed_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=str(clinic["owner"].id),
        start=start + timedelta(hours=1),
    )
    open_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=str(clinic["owner"].id),
        start=start + timedelta(hours=2),
    )

    for appt_id in (paid_id, closed_id, open_id):
        assert client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers).status_code == 200

    paid = client.post(
        f"/api/v1/appointments/{paid_id}/close",
        headers=headers,
        json={"closure_type": "paid", "amount": "10000", "method": "cash"},
    )
    assert paid.status_code == 200, paid.text
    closed = client.post(
        f"/api/v1/appointments/{closed_id}/close",
        headers=headers,
        json={"closure_type": "pending", "amount": "10000"},
    )
    assert closed.status_code == 200, closed.text

    listed = client.get("/api/v1/appointments/to-resolve?kind=unclosed", headers=headers)
    ids = _ids(listed)
    assert open_id in ids
    assert paid_id not in ids
    assert closed_id not in ids


@patch("app.services.appointment_service.ReminderService")
def test_overdue_includes_pending(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime.now(timezone.utc) - timedelta(hours=3)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )

    listed = client.get("/api/v1/appointments/to-resolve?kind=overdue", headers=headers)
    assert appt_id in _ids(listed)


@patch("app.services.appointment_service.ReminderService")
def test_overdue_includes_confirmed(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime.now(timezone.utc) - timedelta(hours=3)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )
    confirm = client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text

    listed = client.get("/api/v1/appointments/to-resolve?kind=overdue", headers=headers)
    assert appt_id in _ids(listed)


@patch("app.services.appointment_service.ReminderService")
def test_overdue_excludes_future_pending(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime.now(timezone.utc) + timedelta(hours=3)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )

    listed = client.get("/api/v1/appointments/to-resolve?kind=overdue", headers=headers)
    assert appt_id not in _ids(listed)


@patch("app.services.appointment_service.ReminderService")
def test_to_resolve_excludes_other_organization(mock_reminder_cls, api_client, db_session: Session):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    own_start = datetime.now(timezone.utc) - timedelta(hours=2)
    own_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=own_start,
    )

    now = datetime.now(timezone.utc)
    other_org = Organization(id=uuid4(), name="Otra Clínica", slug="otra-clinica-resolver")
    other_user = User(
        id=uuid4(),
        organization_id=other_org.id,
        email="other-resolver@example.com",
        full_name="Other Owner",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
        created_at=now,
        updated_at=now,
    )
    other_patient = Patient(
        id=uuid4(),
        organization_id=other_org.id,
        first_name="Luis",
        last_name="Otro",
        dni="30999888",
        created_at=now,
        updated_at=now,
    )
    other_appt = Appointment(
        id=uuid4(),
        organization_id=other_org.id,
        patient_id=other_patient.id,
        professional_id=other_user.id,
        start_at=now - timedelta(hours=4),
        end_at=now - timedelta(hours=3, minutes=30),
        status=AppointmentStatus.PENDING,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([other_org, other_user, other_patient, other_appt])
    db_session.commit()

    listed = client.get("/api/v1/appointments/to-resolve?kind=overdue", headers=headers)
    ids = _ids(listed)
    assert own_id in ids
    assert str(other_appt.id) not in ids


@patch("app.services.appointment_service.ReminderService")
def test_professional_does_not_see_other_professional_appointments(mock_reminder_cls, api_client):
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, owner_headers)
    start = datetime.now(timezone.utc) - timedelta(hours=3)
    own_id = _create_appointment(
        client, owner_headers, patient_id=patient_id, professional_id=str(clinic["prof_a"].id), start=start,
    )
    other_id = _create_appointment(
        client,
        owner_headers,
        patient_id=patient_id,
        professional_id=str(clinic["prof_b"].id),
        start=start + timedelta(minutes=40),
    )

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    listed = client.get("/api/v1/appointments/to-resolve?kind=overdue", headers=prof_headers)
    ids = _ids(listed)
    assert own_id in ids
    assert other_id not in ids

    bypass = client.get(
        f"/api/v1/appointments/to-resolve?kind=overdue&professional_id={clinic['prof_b'].id}",
        headers=prof_headers,
    )
    bypass_ids = _ids(bypass)
    assert own_id in bypass_ids
    assert other_id not in bypass_ids


def test_invalid_kind_returns_422(api_client):
    client, clinic = api_client
    headers = _login(client, clinic["owner"].email, clinic["password"])
    resp = client.get("/api/v1/appointments/to-resolve?kind=invalid", headers=headers)
    assert resp.status_code == 422
