"""Cobertura API de casos de aceptación QA (AGD, PAY, OS, REP, TEA, CAL)."""

import json
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
from app.core.timezone import local_day_bounds_utc, now_local, org_timezone
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    InsuranceClaimStatus,
    PaymentMethod,
    PaymentStatus,
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
    return _create_named_patient(client, headers, "María", "García", "27123456")


def _create_named_patient(
    client: TestClient, headers: dict, first_name: str, last_name: str, dni: str,
) -> str:
    resp = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "first_name": first_name,
            "last_name": last_name,
            "dni": dni,
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


def _create_hi(client: TestClient, headers: dict, name: str = "OSDE") -> str:
    hi = client.post(
        "/api/v1/health-insurances",
        headers=headers,
        json={"name": name, "coverage_percent": 80, "estimated_payment_days": 30},
    )
    assert hi.status_code == 201, hi.text
    return hi.json()["id"]


def _os_close_for_professional(
    client: TestClient,
    headers: dict,
    *,
    professional_id: str,
    first_name: str,
    last_name: str,
    dni: str,
    start: datetime,
    hi_id: str,
) -> tuple[str, str]:
    """Cierra un turno OS del profesional. Devuelve (appointment_id, claim_id)."""
    patient_id = _create_named_patient(client, headers, first_name, last_name, dni)
    appt_id = _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        professional_id=professional_id,
        start=start,
        attention_type="health_insurance",
        health_insurance_id=hi_id,
    )
    attend = client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    assert attend.status_code == 200, attend.text
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
    match = next(c for c in claims.json()["data"] if c["appointment_id"] == appt_id)
    return appt_id, match["id"]


def _payment_fingerprint(db_session: Session, appointment_id: str) -> list[tuple]:
    rows = db_session.execute(
        select(Payment.id, Payment.status, Payment.amount, Payment.updated_at).where(
            Payment.appointment_id == UUID(appointment_id),
        ),
    ).all()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


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
def test_os_professional_can_collect_own_claim(mock_reminder_cls, api_client):
    """Professional A puede marcar collected su propio reclamo OS."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    hi_id = _create_hi(client, owner_headers)
    appt_id, claim_id = _os_close_for_professional(
        client, owner_headers,
        professional_id=str(clinic["prof_a"].id),
        first_name="Ana", last_name="Alvarez", dni="41000001",
        start=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        hi_id=hi_id,
    )

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    collected = client.patch(
        f"/api/v1/insurance-claims/{claim_id}",
        headers=prof_headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"

    appt = client.get(f"/api/v1/appointments/{appt_id}", headers=owner_headers).json()
    assert appt["closure_status"] == "paid"


@patch("app.services.appointment_service.ReminderService")
def test_os_professional_cannot_collect_other_professional_claim(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Professional A no puede marcar collected el reclamo OS de B (403, sin side-effects)."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    hi_id = _create_hi(client, owner_headers)
    appt_b, claim_b = _os_close_for_professional(
        client, owner_headers,
        professional_id=str(clinic["prof_b"].id),
        first_name="Beto", last_name="Benitez", dni="41000002",
        start=datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc),
        hi_id=hi_id,
    )
    payments_before = _payment_fingerprint(db_session, appt_b)
    db_session.expire_all()
    appt_before = db_session.get(Appointment, UUID(appt_b))
    claim_before = db_session.get(InsuranceClaim, UUID(claim_b))
    assert appt_before.closure_status == AppointmentClosureStatus.INSURANCE_PENDING
    assert claim_before.status == InsuranceClaimStatus.PENDING

    prof_a_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    denied = client.patch(
        f"/api/v1/insurance-claims/{claim_b}",
        headers=prof_a_headers,
        json={"status": "collected"},
    )
    assert denied.status_code == 403, denied.text

    db_session.expire_all()
    appt_after = db_session.get(Appointment, UUID(appt_b))
    claim_after = db_session.get(InsuranceClaim, UUID(claim_b))
    assert claim_after.status == InsuranceClaimStatus.PENDING
    assert claim_after.collected_at is None
    assert appt_after.closure_status == AppointmentClosureStatus.INSURANCE_PENDING
    assert _payment_fingerprint(db_session, appt_b) == payments_before


@patch("app.services.appointment_service.ReminderService")
def test_os_owner_and_staff_can_collect_other_professional_claim(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Owner y staff pueden cobrar el reclamo OS de Professional B."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    hi_id = _create_hi(client, owner_headers)
    appt_owner, claim_owner = _os_close_for_professional(
        client, owner_headers,
        professional_id=str(clinic["prof_b"].id),
        first_name="Beto", last_name="Benitez", dni="41000003",
        start=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
        hi_id=hi_id,
    )
    collected_owner = client.patch(
        f"/api/v1/insurance-claims/{claim_owner}",
        headers=owner_headers,
        json={"status": "collected"},
    )
    assert collected_owner.status_code == 200, collected_owner.text
    assert collected_owner.json()["status"] == "collected"
    assert client.get(
        f"/api/v1/appointments/{appt_owner}", headers=owner_headers,
    ).json()["closure_status"] == "paid"

    now = datetime.now(timezone.utc)
    staff = User(
        id=uuid4(),
        organization_id=clinic["org"].id,
        email="staff@example.com",
        full_name="Staff QA",
        password_hash=hash_password(clinic["password"]),
        role=UserRole.STAFF,
        created_at=now,
        updated_at=now,
    )
    db_session.add(staff)
    db_session.commit()
    appt_staff, claim_staff = _os_close_for_professional(
        client, owner_headers,
        professional_id=str(clinic["prof_b"].id),
        first_name="Carla", last_name="Costa", dni="41000004",
        start=datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc),
        hi_id=hi_id,
    )
    staff_headers = _login(client, staff.email, clinic["password"])
    collected_staff = client.patch(
        f"/api/v1/insurance-claims/{claim_staff}",
        headers=staff_headers,
        json={"status": "collected"},
    )
    assert collected_staff.status_code == 200, collected_staff.text
    assert collected_staff.json()["status"] == "collected"
    assert client.get(
        f"/api/v1/appointments/{appt_staff}", headers=owner_headers,
    ).json()["closure_status"] == "paid"


@patch("app.services.appointment_service.ReminderService")
def test_os_professional_cannot_patch_foreign_org_claim(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Un reclamo de otra organización sigue inaccesible."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    now = datetime.now(timezone.utc)
    org2 = Organization(id=uuid4(), name="Otra", slug="otra-org-claim")
    user2 = User(
        id=uuid4(),
        organization_id=org2.id,
        email="otra-claim@example.com",
        full_name="Dr Otra",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
        created_at=now,
        updated_at=now,
    )
    patient2 = Patient(
        id=uuid4(),
        organization_id=org2.id,
        first_name="Zeta",
        last_name="Extranjero",
        dni="41000999",
        created_at=now,
        updated_at=now,
    )
    hi2 = HealthInsurance(id=uuid4(), organization_id=org2.id, name="Swiss")
    claim2 = InsuranceClaim(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        appointment_id=None,
        health_insurance_id=hi2.id,
        expected_amount=Decimal("15000"),
        service_date=date(2026, 11, 10),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add_all([org2, user2, patient2, hi2, claim2])
    db_session.commit()

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    denied = client.patch(
        f"/api/v1/insurance-claims/{claim2.id}",
        headers=prof_headers,
        json={"status": "collected"},
    )
    assert denied.status_code == 404, denied.text
    db_session.expire_all()
    assert db_session.get(InsuranceClaim, claim2.id).status == InsuranceClaimStatus.PENDING


@patch("app.services.appointment_service.ReminderService")
def test_os_professional_can_collect_claim_without_appointment(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Reclamo sin appointment_id sigue org-wide: professional puede marcar collected."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    hi_id = _create_hi(client, owner_headers)
    patient_id = _create_named_patient(client, owner_headers, "Nora", "Nunez", "41000005")
    claim = InsuranceClaim(
        id=uuid4(),
        organization_id=clinic["org"].id,
        patient_id=UUID(patient_id),
        appointment_id=None,
        health_insurance_id=UUID(hi_id),
        expected_amount=Decimal("12000"),
        service_date=date(2026, 11, 10),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add(claim)
    db_session.commit()

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    collected = client.patch(
        f"/api/v1/insurance-claims/{claim.id}",
        headers=prof_headers,
        json={"status": "collected"},
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["status"] == "collected"
    assert collected.json()["appointment_id"] is None


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


def _close_partial(client: TestClient, headers: dict, appt_id: str) -> None:
    attend = client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    assert attend.status_code == 200, attend.text
    closed = client.post(
        f"/api/v1/appointments/{appt_id}/close",
        headers=headers,
        json={"closure_type": "partial", "amount": "10000", "paid_amount": "2000", "method": "cash"},
    )
    assert closed.status_code == 200, closed.text


@patch("app.services.appointment_service.ReminderService")
def test_professional_export_debt_excludes_other_professional(
    mock_reminder_cls, api_client,
):
    """Professional A exporta solo su deuda; owner ve A y B."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_a = _create_named_patient(client, owner_headers, "Ana", "Alvarez", "40000001")
    patient_b = _create_named_patient(client, owner_headers, "Beto", "Benitez", "40000002")
    day = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    appt_a = _create_appointment(
        client, owner_headers,
        patient_id=patient_a, professional_id=str(clinic["prof_a"].id), start=day,
    )
    appt_b = _create_appointment(
        client, owner_headers,
        patient_id=patient_b, professional_id=str(clinic["prof_b"].id),
        start=day + timedelta(hours=3),
    )
    _close_partial(client, owner_headers, appt_a)
    _close_partial(client, owner_headers, appt_b)

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    listed = client.get("/api/v1/payments/items?tab=private", headers=prof_headers)
    assert listed.status_code == 200, listed.text
    assert {row["patient_name"] for row in listed.json()} == {"Alvarez, Ana"}

    debt_a = client.get("/api/v1/exports/debt?format=csv", headers=prof_headers)
    assert debt_a.status_code == 200, debt_a.text
    body_a = debt_a.content.decode("utf-8-sig")
    assert "Alvarez, Ana" in body_a
    assert "Benitez, Beto" not in body_a

    debt_owner = client.get("/api/v1/exports/debt?format=csv", headers=owner_headers)
    assert debt_owner.status_code == 200, debt_owner.text
    body_owner = debt_owner.content.decode("utf-8-sig")
    assert "Alvarez, Ana" in body_owner
    assert "Benitez, Beto" in body_owner


@patch("app.services.appointment_service.ReminderService")
def test_professional_export_payments_uses_payment_professional_id(
    mock_reminder_cls, api_client,
):
    """Export de cobros sigue Payment.professional_id, no el profesional del turno."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    prof_a_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    patient_a = _create_named_patient(client, owner_headers, "Ana", "Alvarez", "40000011")
    patient_b = _create_named_patient(client, owner_headers, "Beto", "Benitez", "40000012")
    day = datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)
    appt_a = _create_appointment(
        client, owner_headers,
        patient_id=patient_a, professional_id=str(clinic["prof_a"].id), start=day,
    )
    appt_b = _create_appointment(
        client, owner_headers,
        patient_id=patient_b, professional_id=str(clinic["prof_b"].id),
        start=day + timedelta(hours=3),
    )
    # A cierra su turno → Payment.professional_id = A
    _close_partial(client, prof_a_headers, appt_a)
    # Owner cierra el turno de B → Payment.professional_id = owner, no B
    _close_partial(client, owner_headers, appt_b)

    recent_a = client.get("/api/v1/payments/items?tab=recent", headers=prof_a_headers)
    assert recent_a.status_code == 200, recent_a.text
    recent_names = {row["patient_name"] for row in recent_a.json()}

    exported = client.get("/api/v1/exports/payments?format=csv", headers=prof_a_headers)
    assert exported.status_code == 200, exported.text
    body = exported.content.decode("utf-8-sig")
    assert "Alvarez, Ana" in body
    assert "Benitez, Beto" not in body
    assert "Alvarez, Ana" in recent_names
    assert "Benitez, Beto" not in recent_names


@patch("app.services.appointment_service.ReminderService")
def test_professional_exports_isolate_organization(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Deuda y cobros de otra organización no aparecen en el export."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    patient_a = _create_named_patient(client, owner_headers, "Ana", "Alvarez", "40000021")
    day = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)
    appt_a = _create_appointment(
        client, owner_headers,
        patient_id=patient_a, professional_id=str(clinic["prof_a"].id), start=day,
    )
    _close_partial(client, owner_headers, appt_a)

    now = datetime.now(timezone.utc)
    org2 = Organization(id=uuid4(), name="Otra", slug="otra-org")
    user2 = User(
        id=uuid4(),
        organization_id=org2.id,
        email="otra@example.com",
        full_name="Dr Otra",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
        created_at=now,
        updated_at=now,
    )
    patient2 = Patient(
        id=uuid4(),
        organization_id=org2.id,
        first_name="Zeta",
        last_name="Extranjero",
        dni="99999999",
        created_at=now,
        updated_at=now,
    )
    start = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    appt2 = Appointment(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        professional_id=user2.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.PENDING,
        expected_amount=Decimal("7777"),
        created_at=now,
        updated_at=now,
    )
    pay2 = Payment(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        appointment_id=appt2.id,
        professional_id=user2.id,
        amount=Decimal("7777"),
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    pay2_paid = Payment(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        appointment_id=appt2.id,
        professional_id=user2.id,
        amount=Decimal("1111"),
        method=PaymentMethod.CASH,
        status=PaymentStatus.PAID,
        paid_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([org2, user2, patient2, appt2, pay2, pay2_paid])
    db_session.commit()

    prof_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    debt = client.get("/api/v1/exports/debt?format=csv", headers=prof_headers)
    payments = client.get("/api/v1/exports/payments?format=csv", headers=prof_headers)
    assert debt.status_code == 200, debt.text
    assert payments.status_code == 200, payments.text
    combined = debt.content.decode("utf-8-sig") + payments.content.decode("utf-8-sig")
    assert "Extranjero" not in combined
    assert "Alvarez, Ana" in debt.content.decode("utf-8-sig")


def _dashboard(client: TestClient, headers: dict) -> dict:
    resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _payments_summary(client: TestClient, headers: dict) -> dict:
    resp = client.get("/api/v1/payments/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _local_today_slot(org: Organization, hour: int) -> datetime:
    """Instante UTC que cae dentro del día local del consultorio, no del servidor."""
    tz = org_timezone(org)
    day_start, _ = local_day_bounds_utc(now_local(tz).date(), tz)
    return day_start + timedelta(hours=hour)


def _attend(client: TestClient, headers: dict, appt_id: str) -> None:
    resp = client.post(f"/api/v1/appointments/{appt_id}/attend", headers=headers)
    assert resp.status_code == 200, resp.text


def _seed_dashboard_scenario(client: TestClient, headers: dict, clinic) -> dict:
    """Universo simétrico para prof A y prof B: un caso de cada métrica por profesional.

    Los turnos de "hoy" quedan atendidos y cobrados a propósito para que solo
    incidan en appointments_today y no contaminen el resto de los contadores.
    """
    prof_a = str(clinic["prof_a"].id)
    prof_b = str(clinic["prof_b"].id)
    hi_id = _create_hi(client, headers, "OSDE Dashboard")
    now = datetime.now(timezone.utc)
    ids: dict[str, str] = {"hi_id": hi_id}

    for tag, prof, hour, person in (
        ("a", prof_a, 9, ("Tania", "Torres", "42000001")),
        ("b", prof_b, 10, ("Ulises", "Urban", "42000002")),
    ):
        appt = _create_appointment(
            client, headers,
            patient_id=_create_named_patient(client, headers, *person),
            professional_id=prof,
            start=_local_today_slot(clinic["org"], hour),
        )
        _attend(client, headers, appt)
        closed = client.post(
            f"/api/v1/appointments/{appt}/close",
            headers=headers,
            json={"closure_type": "paid", "amount": "10000", "method": "cash"},
        )
        assert closed.status_code == 200, closed.text
        ids[f"today_{tag}"] = appt

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Ana", "Alvarez", "42000003")),
        ("b", prof_b, 1, ("Beto", "Benitez", "42000004")),
    ):
        patient_id = _create_named_patient(client, headers, *person)
        ids[f"upcoming_patient_{tag}"] = patient_id
        ids[f"upcoming_{tag}"] = _create_appointment(
            client, headers,
            patient_id=patient_id,
            professional_id=prof,
            start=now + timedelta(days=30, hours=offset),
        )

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Carla", "Costa", "42000005")),
        ("b", prof_b, 1, ("Diego", "Duarte", "42000006")),
    ):
        appt = _create_appointment(
            client, headers,
            patient_id=_create_named_patient(client, headers, *person),
            professional_id=prof,
            start=now - timedelta(days=3) + timedelta(hours=offset),
        )
        _attend(client, headers, appt)
        ids[f"unclosed_{tag}"] = appt

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Elsa", "Etchart", "42000007")),
        ("b", prof_b, 1, ("Fabio", "Ferrari", "42000008")),
    ):
        ids[f"overdue_{tag}"] = _create_appointment(
            client, headers,
            patient_id=_create_named_patient(client, headers, *person),
            professional_id=prof,
            start=now - timedelta(days=4) + timedelta(hours=offset),
        )

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Gina", "Gomez", "42000009")),
        ("b", prof_b, 1, ("Hugo", "Herrera", "42000010")),
    ):
        appt = _create_appointment(
            client, headers,
            patient_id=_create_named_patient(client, headers, *person),
            professional_id=prof,
            start=now - timedelta(days=5) + timedelta(hours=offset),
        )
        no_show = client.post(f"/api/v1/appointments/{appt}/no-show", headers=headers)
        assert no_show.status_code == 200, no_show.text
        ids[f"no_show_{tag}"] = appt

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Iris", "Ibarra", "42000011")),
        ("b", prof_b, 1, ("Juan", "Juarez", "42000012")),
    ):
        patient_id = _create_named_patient(client, headers, *person)
        ids[f"debt_patient_{tag}"] = patient_id
        appt = _create_appointment(
            client, headers,
            patient_id=patient_id,
            professional_id=prof,
            start=now - timedelta(days=6) + timedelta(hours=offset),
        )
        _close_partial(client, headers, appt)
        ids[f"debt_{tag}"] = appt

    for tag, prof, offset, person in (
        ("a", prof_a, 0, ("Kira", "Klein", "42000013")),
        ("b", prof_b, 1, ("Luis", "Lopez", "42000014")),
    ):
        appt, claim = _os_close_for_professional(
            client, headers,
            professional_id=prof,
            first_name=person[0], last_name=person[1], dni=person[2],
            start=now - timedelta(days=7) + timedelta(hours=offset),
            hi_id=hi_id,
        )
        ids[f"claim_{tag}"] = claim
    return ids


def _make_staff(db_session: Session, clinic) -> User:
    now = datetime.now(timezone.utc)
    staff = User(
        id=uuid4(),
        organization_id=clinic["org"].id,
        email="staff-dashboard@example.com",
        full_name="Staff Dashboard",
        password_hash=hash_password(clinic["password"]),
        role=UserRole.STAFF,
        created_at=now,
        updated_at=now,
    )
    db_session.add(staff)
    db_session.commit()
    return staff


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_scopes_counters_by_professional(mock_reminder_cls, api_client):
    """Cada contador del summary refleja solo el universo del profesional."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    _seed_dashboard_scenario(client, owner_headers, clinic)

    a = _dashboard(client, _login(client, clinic["prof_a"].email, clinic["password"]))
    b = _dashboard(client, _login(client, clinic["prof_b"].email, clinic["password"]))
    owner = _dashboard(client, owner_headers)

    for field in (
        "appointments_today",
        "upcoming_unconfirmed",
        "unclosed_attended",
        "overdue_unresolved",
        "no_shows_last_30_days",
    ):
        assert a[field] == 1, field
        assert b[field] == 1, field
        assert owner[field] == 2, field


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_upcoming_hides_other_professional_patients(
    mock_reminder_cls, api_client,
):
    """upcoming_appointments no puede filtrar pacientes ni DNI de otro profesional."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    ids = _seed_dashboard_scenario(client, owner_headers, clinic)

    a = _dashboard(client, _login(client, clinic["prof_a"].email, clinic["password"]))
    upcoming = a["upcoming_appointments"]
    assert [row["id"] for row in upcoming] == [ids["upcoming_a"]]
    assert {row["professional_id"] for row in upcoming} == {str(clinic["prof_a"].id)}
    assert {row["patient"]["last_name"] for row in upcoming} == {"Alvarez"}

    raw_a = json.dumps(a)
    assert "Alvarez" in raw_a
    assert "Benitez" not in raw_a
    assert "42000004" not in raw_a
    assert ids["upcoming_b"] not in raw_a
    assert ids["upcoming_patient_b"] not in raw_a

    owner = _dashboard(client, owner_headers)
    assert {row["id"] for row in owner["upcoming_appointments"]} == {
        ids["upcoming_a"], ids["upcoming_b"],
    }


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_debt_matches_payments_summary(mock_reminder_cls, api_client):
    """Dashboard y /payments/summary comparten fuente y criterio de deuda."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    _seed_dashboard_scenario(client, owner_headers, clinic)
    a_headers = _login(client, clinic["prof_a"].email, clinic["password"])

    for headers in (a_headers, owner_headers):
        dash = _dashboard(client, headers)
        pay = _payments_summary(client, headers)
        assert Decimal(dash["private_debt_total"]) == Decimal(pay["private_debt_total"])
        assert Decimal(dash["insurance_debt_total"]) == Decimal(pay["insurance_debt_total"])
        assert dash["pending_insurance_claims"] == pay["pending_insurance_claims"]

    a = _dashboard(client, a_headers)
    owner = _dashboard(client, owner_headers)
    assert Decimal(a["private_debt_total"]) == Decimal("8000")
    assert Decimal(a["insurance_debt_total"]) == Decimal("45000")
    assert a["pending_insurance_claims"] == 1
    assert a["patients_with_debt"] == 1
    assert Decimal(owner["private_debt_total"]) == Decimal("16000")
    assert Decimal(owner["insurance_debt_total"]) == Decimal("90000")
    assert owner["pending_insurance_claims"] == 2
    assert owner["patients_with_debt"] == 2

    items = client.get("/api/v1/payments/items?tab=private", headers=a_headers)
    assert items.status_code == 200, items.text
    assert a["patients_with_debt"] == len({row["patient_id"] for row in items.json()})


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_matches_to_resolve_for_professional(mock_reminder_cls, api_client):
    """unclosed/overdue del dashboard coinciden con /appointments/to-resolve."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    ids = _seed_dashboard_scenario(client, owner_headers, clinic)
    a_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    a = _dashboard(client, a_headers)

    for kind, field, expected_id in (
        ("unclosed", "unclosed_attended", ids["unclosed_a"]),
        ("overdue", "overdue_unresolved", ids["overdue_a"]),
    ):
        listed = client.get(f"/api/v1/appointments/to-resolve?kind={kind}", headers=a_headers)
        assert listed.status_code == 200, listed.text
        rows = listed.json()
        assert len(rows) == a[field], kind
        assert {row["id"] for row in rows} == {expected_id}


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_owner_and_staff_stay_org_wide(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Owner y staff siguen viendo A + B sin recorte."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    _seed_dashboard_scenario(client, owner_headers, clinic)
    staff = _make_staff(db_session, clinic)

    owner = _dashboard(client, owner_headers)
    staff_view = _dashboard(client, _login(client, staff.email, clinic["password"]))
    assert staff_view == owner

    raw_owner = json.dumps(owner)
    assert "Alvarez" in raw_owner
    assert "Benitez" in raw_owner


@patch("app.services.appointment_service.ReminderService")
def test_dashboard_summary_isolates_second_organization(
    mock_reminder_cls, api_client, db_session: Session,
):
    """Ningún dato de otra organización aparece en el summary."""
    client, clinic = api_client
    mock_reminder_cls.return_value.schedule_for_appointment.return_value = None
    owner_headers = _login(client, clinic["owner"].email, clinic["password"])
    _seed_dashboard_scenario(client, owner_headers, clinic)
    a_headers = _login(client, clinic["prof_a"].email, clinic["password"])
    before = {
        "owner": _dashboard(client, owner_headers),
        "prof_a": _dashboard(client, a_headers),
    }

    now = datetime.now(timezone.utc)
    org2 = Organization(id=uuid4(), name="Otra", slug="otra-org-dashboard")
    owner2 = User(
        id=uuid4(),
        organization_id=org2.id,
        email="otra-dashboard@example.com",
        full_name="Dr Otra",
        password_hash=hash_password(clinic["password"]),
        role=UserRole.OWNER,
        created_at=now,
        updated_at=now,
    )
    patient2 = Patient(
        id=uuid4(),
        organization_id=org2.id,
        first_name="Zoe",
        last_name="Extranjera",
        dni="49999999",
        created_at=now,
        updated_at=now,
    )
    appt2 = Appointment(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        professional_id=owner2.id,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, minutes=30),
        status=AppointmentStatus.PENDING,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
        created_at=now,
        updated_at=now,
    )
    pay2 = Payment(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        appointment_id=appt2.id,
        amount=Decimal("99999"),
        method=PaymentMethod.CASH,
        status=PaymentStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    hi2 = HealthInsurance(id=uuid4(), organization_id=org2.id, name="Swiss Dashboard")
    claim2 = InsuranceClaim(
        id=uuid4(),
        organization_id=org2.id,
        patient_id=patient2.id,
        appointment_id=None,
        health_insurance_id=hi2.id,
        expected_amount=Decimal("77777"),
        service_date=now.date(),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add_all([org2, owner2, patient2, appt2, pay2, hi2, claim2])
    db_session.commit()

    for key, headers in (("owner", owner_headers), ("prof_a", a_headers)):
        summary = _dashboard(client, headers)
        assert summary == before[key], key
        raw = json.dumps(summary)
        assert "Extranjera" not in raw
        assert "49999999" not in raw

    other = _dashboard(client, _login(client, owner2.email, clinic["password"]))
    assert Decimal(other["private_debt_total"]) == Decimal("99999")
    assert Decimal(other["insurance_debt_total"]) == Decimal("77777")
    assert other["patients_with_debt"] == 1


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
