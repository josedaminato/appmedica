"""Tests de alertas del dashboard y endpoint GET /dashboard/alerts."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_current_user
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
from app.services.dashboard_alerts_service import DashboardAlertsService


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
        Payment.__table__,
        HealthInsurance.__table__,
        InsuranceClaim.__table__,
    )
    for table in tables:
        table.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_alerts_data(session: Session) -> tuple[Organization, User, Patient]:
    org = Organization(id=uuid4(), name="Alertas Test", slug="alertas-test")
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@alertas.test",
        full_name="Owner Test",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Deuda",
        dni="30123456",
    )
    insurance = HealthInsurance(
        id=uuid4(),
        organization_id=org.id,
        name="OSDE",
        coverage_percent=80,
        estimated_payment_days=30,
    )
    session.add_all([org, user, patient, insurance])
    session.flush()

    start = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
    partial_appt = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=user.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.PARTIAL,
        expected_amount=Decimal("10000"),
    )
    session.add(partial_appt)
    session.add(
        Payment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient.id,
            appointment_id=partial_appt.id,
            professional_id=user.id,
            amount=Decimal("6000"),
            method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING,
        )
    )

    session.add(
        Payment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient.id,
            professional_id=user.id,
            amount=Decimal("3000"),
            method=PaymentMethod.TRANSFER,
            status=PaymentStatus.PENDING,
        )
    )

    old_service_date = date.today() - timedelta(days=60)
    session.add(
        InsuranceClaim(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient.id,
            health_insurance_id=insurance.id,
            expected_amount=Decimal("15000"),
            service_date=old_service_date,
            status=InsuranceClaimStatus.INVOICED,
        )
    )

    session.commit()
    return org, user, patient


def test_get_alerts_returns_without_name_error(db_session: Session):
    org, _, patient = _seed_alerts_data(db_session)
    alerts = DashboardAlertsService(db_session).get_alerts(org.id)
    assert alerts.unclosed_attended.count >= 0
    assert alerts.overdue_unresolved.count >= 0


def test_top_debt_patients(db_session: Session):
    org, _, patient = _seed_alerts_data(db_session)
    alerts = DashboardAlertsService(db_session).get_alerts(org.id)
    assert len(alerts.top_debt_patients.items) >= 1
    top = alerts.top_debt_patients.items[0]
    assert top.patient_id == patient.id
    assert top.total_debt > 0
    assert top.private_debt > 0
    assert top.insurance_debt > 0


def test_old_insurance_claims(db_session: Session):
    org, _, _ = _seed_alerts_data(db_session)
    alerts = DashboardAlertsService(db_session).get_alerts(org.id, claims_old_days=45)
    assert len(alerts.old_insurance_claims.items) >= 1
    item = alerts.old_insurance_claims.items[0]
    assert item.name == "OSDE"
    assert item.claims_count >= 1
    assert item.debt_total > 0
    assert item.avg_days_pending >= 45


def test_partial_payments_pending(db_session: Session):
    org, _, _ = _seed_alerts_data(db_session)
    alerts = DashboardAlertsService(db_session).get_alerts(org.id)
    partial = alerts.partial_payments_pending
    assert partial.count >= 1
    assert partial.pending_total > 0


@pytest.fixture()
def api_client(db_session: Session):
    org, user, _ = _seed_alerts_data(db_session)
    org_id = user.organization_id

    def override_db():
        yield db_session

    def override_user():
        user.organization_id = org_id
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client, org
    finally:
        app.dependency_overrides.clear()


def test_dashboard_alerts_endpoint_returns_200(api_client):
    client, org = api_client
    response = client.get("/api/v1/dashboard/alerts?claims_old_days=45")
    assert response.status_code == 200
    body = response.json()
    assert body["top_debt_patients"]["items"]
    assert body["old_insurance_claims"]["items"]
    assert body["partial_payments_pending"]["count"] >= 1
    assert body["partial_payments_pending"]["pending_total"]
    assert "unclosed_attended" in body
    assert "overdue_unresolved" in body
