"""Cobertura API de casos de aceptación QA (AGD, PAY, OS, REP, TEA, CAL)."""

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
from app.models.enums import UserRole
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
    org = Organization(id=uuid4(), name="Clínica QA", slug="clinica-qa")
    password = "TestPass123!"
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@example.com",
        full_name="Dr Owner",
        password_hash=hash_password(password),
        role=UserRole.OWNER,
    )
    prof_a = User(
        id=uuid4(),
        organization_id=org.id,
        email="profa@example.com",
        full_name="Dr Prof A",
        password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(),
        organization_id=org.id,
        email="profb@example.com",
        full_name="Dr Prof B",
        password_hash=hash_password(password),
        role=UserRole.PROFESSIONAL,
    )
    db_session.add_all([org, owner, prof_a, prof_b])
    db_session.commit()
    return {
        "org": org,
        "owner": owner,
        "prof_a": prof_a,
        "prof_b": prof_b,
        "password": password,
    }


@pytest.fixture()
def api_client(db_session: Session, seeded_clinic, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REGISTRATION_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    previous_limiter_enabled = limiter.enabled
    limiter.enabled = False

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, seeded_clinic
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        limiter.enabled = previous_limiter_enabled


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_patient(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "first_name": "María",
            "last_name": "García",
            "dni": "27123456",
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
    attention_type: str = "private",
    health_insurance_id: str | None = None,
) -> str:
    payload = {
        "patient_id": patient_id,
        "professional_id": professional_id,
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(minutes=30)).isoformat(),
        "modality": "presencial",
        "attention_type": attention_type,
        "expected_amount": "10000",
    }
    if health_insurance_id:
        payload["health_insurance_id"] = health_insurance_id
    resp = client.post("/api/v1/appointments", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@patch("app.services.appointment_service.ReminderService")
def test_agd04_confirm_appointment(mock_reminder_cls, api_client):
    """AGD-04: confirmar turno pendiente → confirmed."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )

    confirm = client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "confirmed"
    assert mock_reminder_cls.return_value.schedule_for_appointment.called


@patch("app.services.appointment_service.ReminderService")
def test_agd06_no_show_appointment(mock_reminder_cls, api_client):
    """AGD-06: marcar ausente desde confirmado."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )
    client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=headers)

    no_show = client.post(f"/api/v1/appointments/{appt_id}/no-show", headers=headers)
    assert no_show.status_code == 200, no_show.text
    assert no_show.json()["status"] == "no_show"


@patch("app.services.appointment_service.ReminderService")
def test_agd07_cancel_appointment(mock_reminder_cls, api_client):
    """AGD-07: cancelar turno confirmado."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    mock_reminder_cls.return_value.cancel_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )
    client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=headers)

    cancel = client.post(f"/api/v1/appointments/{appt_id}/cancel", headers=headers)
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"
    mock_reminder_cls.return_value.cancel_for_appointment.assert_called_once()


@patch("app.services.appointment_service.ReminderService")
def test_agd08_reschedule_appointment(mock_reminder_cls, api_client):
    """AGD-08: reprogramar turno a nuevo horario."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 4, 14, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client, headers, patient_id=patient_id, professional_id=str(clinic["owner"].id), start=start,
    )
    new_start = datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc)
    new_end = new_start + timedelta(minutes=30)

    reschedule = client.post(
        f"/api/v1/appointments/{appt_id}/reschedule",
        headers=headers,
        json={"start_at": new_start.isoformat(), "end_at": new_end.isoformat()},
    )
    assert reschedule.status_code == 200, reschedule.text
    body = reschedule.json()
    assert body["status"] == "pending"
    assert body["start_at"].startswith("2026-10-05")


@patch("app.services.appointment_service.ReminderService")
def test_os_pipeline_invoiced_collected_pay04(mock_reminder_cls, api_client):
    """OS-03/04 + PAY-04: reclamo pending → facturado → cobrado."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    mock_reminder_cls.return_value.cancel_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])

    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": "OSDE", "coverage_percent": 80, "estimated_payment_days": 30},
    )
    assert hi.status_code == 201, hi.text
    hi_id = hi.json()["id"]

    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=str(clinic["owner"].id),
        start=start,
        attention_type="health_insurance",
        health_insurance_id=hi_id,
    )
    client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    close = client.post(
        f"/api/v1/appointments/{appt_id}/close",
        headers=headers,
        json={
            "closure_type": "insurance_pending",
            "amount": "45000",
            "health_insurance_id": hi_id,
        },
    )
    assert close.status_code == 200, close.text

    claims = client.get("/api/v1/insurance-claims?open_only=true", headers=headers)
    assert claims.status_code == 200, claims.text
    claim_id = claims.json()["data"][0]["id"]
    assert claims.json()["data"][0]["status"] == "pending"

    invoiced = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "invoiced"},
    )
    assert invoiced.status_code == 200, invoiced.text
    assert invoiced.json()["status"] == "invoiced"
    assert invoiced.json()["invoiced_at"] is not None

    collected = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"
    assert collected.json()["collected_at"] is not None


@patch("app.services.appointment_service.ReminderService")
def test_os05_reject_blocked_after_collected(mock_reminder_cls, api_client):
    """OS-05: no se puede rechazar un reclamo ya cobrado."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])

    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": "Swiss", "coverage_percent": 70, "estimated_payment_days": 45},
    )
    hi_id = hi.json()["id"]
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 11, 11, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=str(clinic["owner"].id),
        start=start,
        attention_type="health_insurance",
        health_insurance_id=hi_id,
    )
    client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    client.post(
        f"/api/v1/appointments/{appt_id}/close",
        headers=headers,
        json={"closure_type": "insurance_pending", "amount": "30000", "health_insurance_id": hi_id},
    )
    claim_id = client.get("/api/v1/insurance-claims", headers=headers).json()["data"][0]["id"]
    client.patch(f"/api/v1/insurance-claims/{claim_id}", headers=headers, json={"status": "collected"})

    reject = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "rejected"},
    )
    assert reject.status_code == 400, reject.text


@patch("app.services.appointment_service.ReminderService")
def test_rep_monthly_report_http(mock_reminder_cls, api_client):
    """REP-01..04 (API): reporte mensual y exportación responden 200."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])

    report = client.get("/api/v1/reports/monthly?year=2026&month=6", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["period_label"] == "Junio 2026"
    assert "appointments_total" in body
    assert "total_collected" in body

    xlsx = client.get("/api/v1/reports/monthly/export?year=2026&month=6&format=xlsx", headers=headers)
    assert xlsx.status_code == 200, xlsx.text
    assert "spreadsheet" in xlsx.headers.get("content-type", "")

    csv = client.get("/api/v1/reports/monthly/export?year=2026&month=6&format=csv", headers=headers)
    assert csv.status_code == 200, csv.text
    assert "text/csv" in csv.headers.get("content-type", "")


@patch("app.services.appointment_service.ReminderService")
def test_tea05_professional_sees_only_own_agenda(mock_reminder_cls, api_client):
    """TEA-05: profesional solo ve sus turnos en listado y detalle."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, owner_headers)
    day = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
    appt_a = _create_appointment(
        client, owner_headers,
        patient_id=patient_id, professional_id=str(clinic["prof_a"].id), start=day,
    )
    appt_b = _create_appointment(
        client, owner_headers,
        patient_id=patient_id,
        professional_id=str(clinic["prof_b"].id),
        start=day + timedelta(hours=2),
    )

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    listed = client.get("/api/v1/appointments?date=2026-11-01&view=day", headers=prof_headers)
    assert listed.status_code == 200, listed.text
    ids = {row["id"] for row in listed.json()}
    assert appt_a in ids
    assert appt_b not in ids

    forbidden = client.get(f"/api/v1/appointments/{appt_b}", headers=prof_headers)
    assert forbidden.status_code == 403, forbidden.text


@patch("app.services.appointment_service.ReminderService")
def test_tea06_professional_sees_only_own_debt(mock_reminder_cls, api_client):
    """TEA-06: profesional solo ve deuda de sus turnos."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_id = _create_patient(client, owner_headers)
    day = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)

    appt_a = _create_appointment(
        client, owner_headers,
        patient_id=patient_id, professional_id=str(clinic["prof_a"].id), start=day,
    )
    appt_b = _create_appointment(
        client, owner_headers,
        patient_id=patient_id,
        professional_id=str(clinic["prof_b"].id),
        start=day + timedelta(hours=3),
    )
    for appt_id in (appt_a, appt_b):
        client.post(f"/api/v1/appointments/{appt_id}/attend", headers=owner_headers)
        client.post(
            f"/api/v1/appointments/{appt_id}/close",
            headers=owner_headers,
            json={"closure_type": "partial", "amount": "10000", "paid_amount": "2000", "method": "cash"},
        )

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    items = client.get("/api/v1/payments/items?tab=private", headers=prof_headers)
    assert items.status_code == 200, items.text
    rows = items.json()
    assert len(rows) == 1
    assert rows[0]["appointment_id"] == appt_a

    summary = client.get("/api/v1/payments/summary", headers=prof_headers)
    assert summary.status_code == 200, summary.text
    assert float(summary.json()["private_debt_total"]) == 8000.0


def test_cal04_calendar_feed_token_rotation(api_client):
    """CAL-04: rotar token invalida el enlace anterior."""
    client, clinic = api_client
    headers = _login(client, clinic["owner"].email, clinic["password"])

    feed = client.get("/api/v1/calendar/feed", headers=headers)
    assert feed.status_code == 200, feed.text
    old_url = feed.json()["feed_url"]
    old_token = old_url.rstrip("/").split("/")[-1]

    old_ics = client.get(f"/api/v1/calendar/feed/{old_token}")
    assert old_ics.status_code == 200, old_ics.text

    regen = client.post("/api/v1/calendar/feed/regenerate", headers=headers)
    assert regen.status_code == 200, regen.text
    new_url = regen.json()["feed_url"]
    assert new_url != old_url
    new_token = new_url.rstrip("/").split("/")[-1]

    stale = client.get(f"/api/v1/calendar/feed/{old_token}")
    assert stale.status_code == 404, stale.text

    fresh = client.get(f"/api/v1/calendar/feed/{new_token}")
    assert fresh.status_code == 200, fresh.text
    assert "BEGIN:VCALENDAR" in fresh.text
