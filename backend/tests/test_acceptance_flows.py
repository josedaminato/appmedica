"""Cobertura API de casos de aceptación QA (AGD, PAY, OS, REP, TEA, CAL)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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
    InsuranceClaimStatus,
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
    return resp.json()["appointments"][0]["id"]


def _payment_count(db_session: Session, appointment_id: str) -> int:
    return db_session.scalar(
        select(func.count()).select_from(Payment).where(
            Payment.appointment_id == UUID(appointment_id),
        ),
    ) or 0


def _os_close(client: TestClient, headers: dict, clinic, *, amount: str = "45000") -> tuple[str, str, dict]:
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
            "amount": amount,
            "health_insurance_id": hi_id,
        },
    )
    assert close.status_code == 200, close.text
    return appt_id, hi_id, close.json()


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
def test_os_pipeline_invoiced_collected_pay04(mock_reminder_cls, api_client, db_session: Session):
    """OS-03/04 + PAY-04: reclamo pending → facturado → cobrado; el turno pasa a paid."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    mock_reminder_cls.return_value.cancel_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])

    appt_id, hi_id, closed = _os_close(client, headers, clinic)
    assert closed["closure_status"] == "insurance_pending"
    assert closed["status"] == "attended"
    assert closed["attention_type"] == "health_insurance"
    assert closed["health_insurance_id"] == hi_id
    assert float(closed["expected_amount"]) == 45000

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
    after_invoice = client.get(f"/api/v1/appointments/{appt_id}", headers=headers)
    assert after_invoice.status_code == 200
    assert after_invoice.json()["closure_status"] == "insurance_pending"
    assert after_invoice.json()["status"] == "attended"
    assert after_invoice.json()["attention_type"] == "health_insurance"

    collected = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"
    assert collected.json()["collected_at"] is not None

    after_collect = client.get(f"/api/v1/appointments/{appt_id}", headers=headers)
    assert after_collect.status_code == 200
    body = after_collect.json()
    assert body["closure_status"] == "paid"
    assert body["status"] == "attended"
    assert body["attention_type"] == "health_insurance"
    assert body["health_insurance_id"] == hi_id
    assert _payment_count(db_session, appt_id) == 0

    extra_pay = client.post(
        f"/api/v1/appointments/{appt_id}/payments",
        headers=headers,
        json={"amount": "1000", "method": "cash"},
    )
    assert extra_pay.status_code == 400, extra_pay.text
    assert _payment_count(db_session, appt_id) == 0


@patch("app.services.appointment_service.ReminderService")
def test_os05_reject_blocked_after_collected(mock_reminder_cls, api_client):
    """OS-05: no se puede rechazar un reclamo ya cobrado."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    appt_id, _, _ = _os_close(client, headers, clinic, amount="30000")
    claim_id = client.get("/api/v1/insurance-claims", headers=headers).json()["data"][0]["id"]
    collected = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert client.get(f"/api/v1/appointments/{appt_id}", headers=headers).json()["closure_status"] == "paid"

    reject = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "rejected"},
    )
    assert reject.status_code == 400, reject.text
    assert client.get(f"/api/v1/appointments/{appt_id}", headers=headers).json()["closure_status"] == "paid"


@patch("app.services.appointment_service.ReminderService")
def test_os_rejected_does_not_change_appointment_closure(mock_reminder_cls, api_client, db_session: Session):
    """Rechazar un reclamo no modifica el cierre del turno."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    appt_id, _, _ = _os_close(client, headers, clinic)
    claim_id = client.get("/api/v1/insurance-claims", headers=headers).json()["data"][0]["id"]

    rejected = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=headers,
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    appt = client.get(f"/api/v1/appointments/{appt_id}", headers=headers).json()
    assert appt["closure_status"] == "insurance_pending"
    assert appt["status"] == "attended"
    assert _payment_count(db_session, appt_id) == 0


@patch("app.services.appointment_service.ReminderService")
def test_os_collected_claim_without_appointment(mock_reminder_cls, api_client, db_session: Session):
    """Un reclamo sin turno puede pasar a collected sin error."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": "OSDE", "coverage_percent": 80, "estimated_payment_days": 30},
    )
    assert hi.status_code == 201, hi.text
    patient_id = _create_patient(client, headers)
    claim = InsuranceClaim(
        id=uuid4(),
        organization_id=clinic["org"].id,
        patient_id=UUID(patient_id),
        appointment_id=None,
        health_insurance_id=UUID(hi.json()["id"]),
        expected_amount=Decimal("12000"),
        service_date=date(2026, 10, 10),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add(claim)
    db_session.commit()

    collected = client.patch(
        f"/api/v1/insurance-claims/{claim.id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"
    assert collected.json()["appointment_id"] is None


@patch("app.services.appointment_service.ReminderService")
def test_os_collected_does_not_update_foreign_org_appointment(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Cobrar un reclamo de una org no puede cambiar el turno de otra org."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": "OSDE", "coverage_percent": 80, "estimated_payment_days": 30},
    )
    patient_id = _create_patient(client, headers)

    org_b = Organization(id=uuid4(), name="Otra", slug="otra-org")
    user_b = User(
        id=uuid4(),
        organization_id=org_b.id,
        email="other@example.com",
        full_name="Other Owner",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
    )
    patient_b = Patient(
        id=uuid4(),
        organization_id=org_b.id,
        first_name="Eva",
        last_name="Otro",
        dni="30111222",
    )
    hi_b = HealthInsurance(id=uuid4(), organization_id=org_b.id, name="Swiss")
    start = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
    appt_b = Appointment(
        id=uuid4(),
        organization_id=org_b.id,
        patient_id=patient_b.id,
        professional_id=user_b.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.HEALTH_INSURANCE,
        expected_amount=Decimal("20000"),
        closure_status=AppointmentClosureStatus.INSURANCE_PENDING,
        health_insurance_id=hi_b.id,
    )
    db_session.add_all([org_b, user_b, patient_b, hi_b, appt_b])
    db_session.commit()
    appt_b_id = appt_b.id

    claim = InsuranceClaim(
        id=uuid4(),
        organization_id=clinic["org"].id,
        patient_id=UUID(patient_id),
        appointment_id=appt_b_id,
        health_insurance_id=UUID(hi.json()["id"]),
        expected_amount=Decimal("20000"),
        service_date=date(2026, 10, 12),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add(claim)
    db_session.commit()

    collected = client.patch(
        f"/api/v1/insurance-claims/{claim.id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"

    db_session.expire_all()
    foreign = db_session.get(Appointment, appt_b_id)
    assert foreign is not None
    assert foreign.closure_status == AppointmentClosureStatus.INSURANCE_PENDING
    assert foreign.organization_id == org_b.id

    ghost = InsuranceClaim(
        id=uuid4(),
        organization_id=org_b.id,
        patient_id=patient_b.id,
        appointment_id=appt_b_id,
        health_insurance_id=hi_b.id,
        expected_amount=Decimal("15000"),
        service_date=date(2026, 10, 12),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add(ghost)
    db_session.commit()
    denied = client.patch(
        f"/api/v1/insurance-claims/{ghost.id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert denied.status_code == 404
    db_session.expire_all()
    assert db_session.get(Appointment, appt_b_id).closure_status == AppointmentClosureStatus.INSURANCE_PENDING


@patch("app.services.appointment_service.ReminderService")
def test_os_collected_skips_appointment_not_insurance_pending(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Si el turno no está en insurance_pending, collected no altera el cierre."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    headers = _login(client, clinic["owner"].email, clinic["password"])
    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": "OSDE", "coverage_percent": 80, "estimated_payment_days": 30},
    )
    patient_id = _create_patient(client, headers)
    start = datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc)
    appt_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=str(clinic["owner"].id),
        start=start,
    )
    client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    close = client.post(
        f"/api/v1/appointments/{appt_id}/close",
        headers=headers,
        json={"closure_type": "pending", "amount": "10000", "method": "cash"},
    )
    assert close.status_code == 200, close.text
    assert close.json()["closure_status"] == "pending"

    claim = InsuranceClaim(
        id=uuid4(),
        organization_id=clinic["org"].id,
        patient_id=UUID(patient_id),
        appointment_id=UUID(appt_id),
        health_insurance_id=UUID(hi.json()["id"]),
        expected_amount=Decimal("10000"),
        service_date=date(2026, 10, 13),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add(claim)
    db_session.commit()
    payments_before = _payment_count(db_session, appt_id)

    collected = client.patch(
        f"/api/v1/insurance-claims/{claim.id}",
        headers=headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"

    appt = client.get(f"/api/v1/appointments/{appt_id}", headers=headers).json()
    assert appt["closure_status"] == "pending"
    assert appt["attention_type"] == "private"
    assert _payment_count(db_session, appt_id) == payments_before


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
