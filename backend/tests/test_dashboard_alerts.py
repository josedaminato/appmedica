"""Tests de alertas del dashboard y endpoint GET /dashboard/alerts."""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
from app.schemas.dashboard_alerts import DashboardAlerts
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
    assert alerts.old_insurance_claims.total_count >= item.claims_count


def test_old_insurance_claims_includes_exact_threshold_days(db_session: Session):
    org, _, patient = _seed_alerts_data(db_session)
    insurance = db_session.scalars(
        select(HealthInsurance).where(HealthInsurance.organization_id == org.id),
    ).one()
    exact = InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        health_insurance_id=insurance.id,
        expected_amount=Decimal("2000"),
        service_date=date.today() - timedelta(days=45),
        status=InsuranceClaimStatus.PENDING,
    )
    younger = InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        health_insurance_id=insurance.id,
        expected_amount=Decimal("2000"),
        service_date=date.today() - timedelta(days=44),
        status=InsuranceClaimStatus.PENDING,
    )
    db_session.add_all([exact, younger])
    db_session.commit()

    alerts = DashboardAlertsService(db_session).get_alerts(org.id, claims_old_days=45)
    # seed ya trae un reclamo a 60 días; el de 45 entra y el de 44 no
    assert alerts.old_insurance_claims.total_count == 2
    assert alerts.old_insurance_claims.items[0].claims_count == 2


def test_old_insurance_claims_total_count_includes_beyond_top_six(db_session: Session):
    org, _, patient = _seed_alerts_data(db_session)
    old_service_date = date.today() - timedelta(days=60)
    extra = []
    for i in range(7):
        insurance = HealthInsurance(
            id=uuid4(),
            organization_id=org.id,
            name=f"OS Extra {i}",
        )
        extra.append(insurance)
        extra.append(
            InsuranceClaim(
                id=uuid4(),
                organization_id=org.id,
                patient_id=patient.id,
                health_insurance_id=insurance.id,
                expected_amount=Decimal("1000"),
                service_date=old_service_date,
                status=InsuranceClaimStatus.PENDING,
            )
        )
    db_session.add_all(extra)
    db_session.commit()

    alerts = DashboardAlertsService(db_session).get_alerts(org.id, claims_old_days=45)
    assert len(alerts.old_insurance_claims.items) == 6
    assert alerts.old_insurance_claims.total_count == 8


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
    assert body["old_insurance_claims"]["total_count"] >= 1


def _seed_scoped_alerts_data(session: Session) -> dict:
    """Universo simétrico A/B + claim huérfano + pago registrado por staff en turno de A."""
    now = datetime.now(timezone.utc)
    old_date = date.today() - timedelta(days=60)
    org = Organization(id=uuid4(), name="Alertas Scope", slug="alertas-scope")
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@scope.test",
        full_name="Owner Scope",
        password_hash="x",
        role=UserRole.OWNER,
    )
    prof_a = User(
        id=uuid4(),
        organization_id=org.id,
        email="profa@scope.test",
        full_name="Dr Prof A",
        password_hash="x",
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(),
        organization_id=org.id,
        email="profb@scope.test",
        full_name="Dr Prof B",
        password_hash="x",
        role=UserRole.PROFESSIONAL,
    )
    staff = User(
        id=uuid4(),
        organization_id=org.id,
        email="staff@scope.test",
        full_name="Staff Scope",
        password_hash="x",
        role=UserRole.STAFF,
    )
    insurance = HealthInsurance(
        id=uuid4(),
        organization_id=org.id,
        name="OSDE Scope",
        coverage_percent=80,
        estimated_payment_days=30,
    )
    patient_a = Patient(
        id=uuid4(), organization_id=org.id,
        first_name="Ana", last_name="Alvarez", dni="51000001",
    )
    patient_b = Patient(
        id=uuid4(), organization_id=org.id,
        first_name="Beto", last_name="Benitez", dni="51000002",
    )
    patient_shared = Patient(
        id=uuid4(), organization_id=org.id,
        first_name="Carla", last_name="Costa", dni="51000003",
    )
    session.add_all([
        org, owner, prof_a, prof_b, staff, insurance,
        patient_a, patient_b, patient_shared,
    ])
    session.flush()

    def appt(
        *,
        patient: Patient,
        professional: User,
        start: datetime,
        status: AppointmentStatus,
        closure: AppointmentClosureStatus,
    ) -> Appointment:
        row = Appointment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient.id,
            professional_id=professional.id,
            start_at=start,
            end_at=start + timedelta(minutes=30),
            status=status,
            modality=AppointmentModality.IN_PERSON,
            attention_type=AttentionType.PRIVATE,
            closure_status=closure,
            expected_amount=Decimal("10000"),
        )
        session.add(row)
        return row

    unclosed_a = appt(
        patient=patient_a, professional=prof_a,
        start=now - timedelta(days=2), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.NONE,
    )
    unclosed_b = appt(
        patient=patient_b, professional=prof_b,
        start=now - timedelta(days=2, hours=1), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.NONE,
    )
    overdue_a = appt(
        patient=patient_a, professional=prof_a,
        start=now - timedelta(days=3), status=AppointmentStatus.PENDING,
        closure=AppointmentClosureStatus.NONE,
    )
    overdue_b = appt(
        patient=patient_b, professional=prof_b,
        start=now - timedelta(days=3, hours=1), status=AppointmentStatus.CONFIRMED,
        closure=AppointmentClosureStatus.NONE,
    )

    partial_a = appt(
        patient=patient_a, professional=prof_a,
        start=now - timedelta(days=4), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    partial_b = appt(
        patient=patient_b, professional=prof_b,
        start=now - timedelta(days=4, hours=1), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    session.add(
        Payment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient_a.id,
            appointment_id=partial_a.id,
            professional_id=staff.id,
            amount=Decimal("7000"),
            method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING,
        ),
    )
    session.add(
        Payment(
            id=uuid4(),
            organization_id=org.id,
            patient_id=patient_b.id,
            appointment_id=partial_b.id,
            professional_id=prof_b.id,
            amount=Decimal("8000"),
            method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING,
        ),
    )

    claim_appt_a = appt(
        patient=patient_a, professional=prof_a,
        start=now - timedelta(days=50), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.INSURANCE_PENDING,
    )
    claim_appt_b = appt(
        patient=patient_b, professional=prof_b,
        start=now - timedelta(days=50, hours=1), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.INSURANCE_PENDING,
    )
    claim_a = InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient_a.id,
        appointment_id=claim_appt_a.id,
        health_insurance_id=insurance.id,
        expected_amount=Decimal("12000"),
        service_date=old_date,
        status=InsuranceClaimStatus.PENDING,
    )
    claim_b = InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient_b.id,
        appointment_id=claim_appt_b.id,
        health_insurance_id=insurance.id,
        expected_amount=Decimal("13000"),
        service_date=old_date,
        status=InsuranceClaimStatus.INVOICED,
    )
    orphan_claim = InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient_shared.id,
        appointment_id=None,
        health_insurance_id=insurance.id,
        expected_amount=Decimal("5000"),
        service_date=old_date,
        status=InsuranceClaimStatus.PENDING,
    )
    session.add_all([claim_a, claim_b, orphan_claim])

    debt_a = appt(
        patient=patient_a, professional=prof_a,
        start=now - timedelta(days=6), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    debt_b = appt(
        patient=patient_b, professional=prof_b,
        start=now - timedelta(days=6, hours=1), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    debt_shared_a = appt(
        patient=patient_shared, professional=prof_a,
        start=now - timedelta(days=6, hours=2), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    debt_shared_b = appt(
        patient=patient_shared, professional=prof_b,
        start=now - timedelta(days=6, hours=3), status=AppointmentStatus.ATTENDED,
        closure=AppointmentClosureStatus.PARTIAL,
    )
    session.add_all([
        Payment(
            id=uuid4(), organization_id=org.id, patient_id=patient_a.id,
            appointment_id=debt_a.id, professional_id=staff.id,
            amount=Decimal("4000"), method=PaymentMethod.CASH, status=PaymentStatus.PENDING,
        ),
        Payment(
            id=uuid4(), organization_id=org.id, patient_id=patient_b.id,
            appointment_id=debt_b.id, professional_id=prof_b.id,
            amount=Decimal("5000"), method=PaymentMethod.CASH, status=PaymentStatus.PENDING,
        ),
        Payment(
            id=uuid4(), organization_id=org.id, patient_id=patient_shared.id,
            appointment_id=debt_shared_a.id, professional_id=staff.id,
            amount=Decimal("3000"), method=PaymentMethod.CASH, status=PaymentStatus.PENDING,
        ),
        Payment(
            id=uuid4(), organization_id=org.id, patient_id=patient_shared.id,
            appointment_id=debt_shared_b.id, professional_id=prof_b.id,
            amount=Decimal("6000"), method=PaymentMethod.CASH, status=PaymentStatus.PENDING,
        ),
    ])
    session.commit()
    return {
        "org": org,
        "owner": owner,
        "prof_a": prof_a,
        "prof_b": prof_b,
        "staff": staff,
        "patient_a": patient_a,
        "patient_b": patient_b,
        "patient_shared": patient_shared,
        "orphan_claim": orphan_claim,
    }


def _alerts(session: Session, org_id, *, user_id=None) -> DashboardAlerts:
    kwargs = {}
    if user_id is not None:
        kwargs["professional_id"] = user_id
    return DashboardAlertsService(session).get_alerts(org_id, claims_old_days=45, **kwargs)


def test_alerts_unclosed_and_overdue_scoped_by_professional(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    a = _alerts(db_session, org.id, user_id=data["prof_a"].id)
    b = _alerts(db_session, org.id, user_id=data["prof_b"].id)
    owner = _alerts(db_session, org.id)

    assert a.unclosed_attended.count == 1
    assert b.unclosed_attended.count == 1
    assert owner.unclosed_attended.count == 2

    assert a.overdue_unresolved.count == 1
    assert b.overdue_unresolved.count == 1
    assert owner.overdue_unresolved.count == 2


def test_alerts_partial_payments_scoped_by_professional(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    a = _alerts(db_session, org.id, user_id=data["prof_a"].id)
    b = _alerts(db_session, org.id, user_id=data["prof_b"].id)
    owner = _alerts(db_session, org.id)

    assert a.partial_payments_pending.count == 3
    assert a.partial_payments_pending.pending_total == Decimal("14000")
    assert b.partial_payments_pending.count == 3
    assert b.partial_payments_pending.pending_total == Decimal("19000")
    assert owner.partial_payments_pending.count == 6
    assert owner.partial_payments_pending.pending_total == Decimal("33000")


def test_alerts_old_claims_scoped_and_orphan_visible_only_org_wide(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    a = _alerts(db_session, org.id, user_id=data["prof_a"].id)
    b = _alerts(db_session, org.id, user_id=data["prof_b"].id)
    owner = _alerts(db_session, org.id)

    assert a.old_insurance_claims.total_count == 1
    assert b.old_insurance_claims.total_count == 1
    assert owner.old_insurance_claims.total_count == 3


def test_alerts_top_debt_attributes_by_appointment_not_payment_professional(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    a = _alerts(db_session, org.id, user_id=data["prof_a"].id)
    b = _alerts(db_session, org.id, user_id=data["prof_b"].id)

    a_by_patient = {item.patient_id: item for item in a.top_debt_patients.items}
    assert data["patient_a"].id in a_by_patient
    assert data["patient_b"].id not in a_by_patient
    assert a_by_patient[data["patient_a"].id].private_debt == Decimal("11000")
    assert a_by_patient[data["patient_a"].id].insurance_debt == Decimal("12000")
    assert a_by_patient[data["patient_a"].id].total_debt == Decimal("23000")

    shared = a_by_patient[data["patient_shared"].id]
    assert shared.private_debt == Decimal("3000")
    assert shared.insurance_debt == Decimal("0")
    assert shared.total_debt == Decimal("3000")

    b_by_patient = {item.patient_id: item for item in b.top_debt_patients.items}
    assert data["patient_b"].id in b_by_patient
    assert b_by_patient[data["patient_b"].id].private_debt == Decimal("13000")
    assert b_by_patient[data["patient_b"].id].insurance_debt == Decimal("13000")
    assert b_by_patient[data["patient_shared"].id].private_debt == Decimal("6000")
    assert b_by_patient[data["patient_shared"].id].insurance_debt == Decimal("0")


def test_alerts_owner_and_staff_stay_org_wide(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    owner = _alerts(db_session, org.id)
    staff_view = DashboardAlertsService(db_session).get_alerts(
        org.id, claims_old_days=45, professional_id=None,
    )
    assert staff_view.unclosed_attended.count == owner.unclosed_attended.count == 2
    assert staff_view.top_debt_patients.items
    owner_ids = {item.patient_id for item in owner.top_debt_patients.items}
    assert data["patient_a"].id in owner_ids
    assert data["patient_b"].id in owner_ids


def test_alerts_isolates_second_organization(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]
    before_owner = _alerts(db_session, org.id)
    before_a = _alerts(db_session, org.id, user_id=data["prof_a"].id)

    now = datetime.now(timezone.utc)
    org2 = Organization(id=uuid4(), name="Otra", slug="otra-alerts")
    user2 = User(
        id=uuid4(), organization_id=org2.id, email="otra@alerts.test",
        full_name="Dr Otra", password_hash="x", role=UserRole.OWNER,
    )
    patient2 = Patient(
        id=uuid4(), organization_id=org2.id,
        first_name="Zoe", last_name="Extranjera", dni="51999999",
    )
    session_add = [
        org2, user2, patient2,
        Appointment(
            id=uuid4(), organization_id=org2.id, patient_id=patient2.id,
            professional_id=user2.id, start_at=now - timedelta(days=1),
            end_at=now - timedelta(hours=23), status=AppointmentStatus.ATTENDED,
            modality=AppointmentModality.IN_PERSON, attention_type=AttentionType.PRIVATE,
            closure_status=AppointmentClosureStatus.NONE,
        ),
    ]
    db_session.add_all(session_add)
    db_session.commit()

    assert _alerts(db_session, org.id) == before_owner
    assert _alerts(db_session, org.id, user_id=data["prof_a"].id) == before_a
    other = _alerts(db_session, org2.id)
    assert other.unclosed_attended.count == 1
    assert other.overdue_unresolved.count == 0
    assert other.top_debt_patients.items == []


def test_alerts_professional_json_excludes_patient_b(db_session: Session):
    data = _seed_scoped_alerts_data(db_session)
    org = data["org"]

    def override_db():
        yield db_session

    def override_user():
        return data["prof_a"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app, raise_server_exceptions=True)
    try:
        body = client.get("/api/v1/dashboard/alerts?claims_old_days=45").json()
    finally:
        app.dependency_overrides.clear()

    raw = json.dumps(body)
    assert "Alvarez" in raw or str(data["patient_a"].id) in raw
    assert "Benitez" not in raw
    assert "51000002" not in raw
    assert str(data["patient_b"].id) not in raw
    top_ids = {row["patient_id"] for row in body["top_debt_patients"]["items"]}
    assert data["patient_b"].id not in top_ids

