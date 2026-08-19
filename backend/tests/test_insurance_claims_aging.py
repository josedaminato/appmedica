"""GET /insurance-claims?min_days=45|60|90: antigüedad sobre service_date."""

from datetime import date, timedelta
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
from app.models.enums import InsuranceClaimStatus, UserRole
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
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _org(session: Session, slug: str) -> tuple[Organization, User, Patient, HealthInsurance]:
    org = Organization(id=uuid4(), name=f"Org {slug}", slug=slug)
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email=f"{slug}@test.com",
        full_name="Owner Test",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Reclamo",
        dni=slug[:8].ljust(8, "0"),
    )
    insurance = HealthInsurance(
        id=uuid4(),
        organization_id=org.id,
        name="OSDE",
    )
    session.add_all([org, user, patient, insurance])
    session.flush()
    return org, user, patient, insurance


def _claim(
    org: Organization,
    patient: Patient,
    insurance: HealthInsurance,
    *,
    days_ago: int,
    status: InsuranceClaimStatus,
    amount: Decimal = Decimal("1000"),
) -> InsuranceClaim:
    return InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        health_insurance_id=insurance.id,
        expected_amount=amount,
        service_date=date.today() - timedelta(days=days_ago),
        status=status,
    )


def _client(db_session: Session, user: User) -> TestClient:
    def override_db():
        yield db_session

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app, raise_server_exceptions=True)


def test_min_days_45_includes_exact_threshold_excludes_younger(db_session: Session):
    org, user, patient, insurance = _org(db_session, "age45")
    exact = _claim(org, patient, insurance, days_ago=45, status=InsuranceClaimStatus.PENDING)
    younger = _claim(org, patient, insurance, days_ago=44, status=InsuranceClaimStatus.PENDING)
    older = _claim(org, patient, insurance, days_ago=46, status=InsuranceClaimStatus.INVOICED)
    db_session.add_all([exact, younger, older])
    db_session.commit()

    client = _client(db_session, user)
    try:
        resp = client.get("/api/v1/insurance-claims?min_days=45")
        assert resp.status_code == 200, resp.text
        ids = {row["id"] for row in resp.json()["data"]}
        assert str(exact.id) in ids
        assert str(older.id) in ids
        assert str(younger.id) not in ids
        assert resp.json()["meta"]["total"] == 2
    finally:
        app.dependency_overrides.clear()


def test_min_days_60_and_90_buckets(db_session: Session):
    org, user, patient, insurance = _org(db_session, "age6090")
    d45 = _claim(org, patient, insurance, days_ago=45, status=InsuranceClaimStatus.PENDING)
    d60 = _claim(org, patient, insurance, days_ago=60, status=InsuranceClaimStatus.PENDING)
    d90 = _claim(org, patient, insurance, days_ago=90, status=InsuranceClaimStatus.INVOICED)
    d120 = _claim(org, patient, insurance, days_ago=120, status=InsuranceClaimStatus.PENDING)
    db_session.add_all([d45, d60, d90, d120])
    db_session.commit()

    client = _client(db_session, user)
    try:
        ids_60 = {row["id"] for row in client.get("/api/v1/insurance-claims?min_days=60").json()["data"]}
        ids_90 = {row["id"] for row in client.get("/api/v1/insurance-claims?min_days=90").json()["data"]}
        assert ids_60 == {str(d60.id), str(d90.id), str(d120.id)}
        assert ids_90 == {str(d90.id), str(d120.id)}
        assert str(d45.id) not in ids_60
    finally:
        app.dependency_overrides.clear()


def test_min_days_excludes_collected_and_rejected(db_session: Session):
    org, user, patient, insurance = _org(db_session, "ageclosed")
    pending = _claim(org, patient, insurance, days_ago=70, status=InsuranceClaimStatus.PENDING)
    invoiced = _claim(org, patient, insurance, days_ago=70, status=InsuranceClaimStatus.INVOICED)
    collected = _claim(org, patient, insurance, days_ago=70, status=InsuranceClaimStatus.COLLECTED)
    rejected = _claim(org, patient, insurance, days_ago=70, status=InsuranceClaimStatus.REJECTED)
    db_session.add_all([pending, invoiced, collected, rejected])
    db_session.commit()

    client = _client(db_session, user)
    try:
        ids = {row["id"] for row in client.get("/api/v1/insurance-claims?min_days=45").json()["data"]}
        assert ids == {str(pending.id), str(invoiced.id)}
    finally:
        app.dependency_overrides.clear()


def test_min_days_orders_oldest_first(db_session: Session):
    org, user, patient, insurance = _org(db_session, "ageorder")
    newer = _claim(org, patient, insurance, days_ago=50, status=InsuranceClaimStatus.PENDING)
    older = _claim(org, patient, insurance, days_ago=90, status=InsuranceClaimStatus.INVOICED)
    db_session.add_all([newer, older])
    db_session.commit()

    client = _client(db_session, user)
    try:
        without = client.get("/api/v1/insurance-claims?open_only=true").json()["data"]
        assert [row["id"] for row in without] == [str(newer.id), str(older.id)]

        with_min = client.get("/api/v1/insurance-claims?min_days=45").json()["data"]
        assert [row["id"] for row in with_min] == [str(older.id), str(newer.id)]
    finally:
        app.dependency_overrides.clear()


def test_min_days_isolates_organization(db_session: Session):
    org_a, user_a, patient_a, ins_a = _org(db_session, "age-a")
    org_b, _, patient_b, ins_b = _org(db_session, "age-b")
    claim_a = _claim(org_a, patient_a, ins_a, days_ago=80, status=InsuranceClaimStatus.PENDING, amount=Decimal("1111"))
    claim_b = _claim(org_b, patient_b, ins_b, days_ago=80, status=InsuranceClaimStatus.PENDING, amount=Decimal("9999"))
    db_session.add_all([claim_a, claim_b])
    db_session.commit()

    client = _client(db_session, user_a)
    try:
        body = client.get("/api/v1/insurance-claims?min_days=45").json()
        ids = {row["id"] for row in body["data"]}
        assert ids == {str(claim_a.id)}
        assert str(claim_b.id) not in ids
    finally:
        app.dependency_overrides.clear()


def test_min_days_45_matches_dashboard_old_claims_count(db_session: Session):
    org, user, patient, insurance = _org(db_session, "agedash")
    db_session.add_all([
        _claim(org, patient, insurance, days_ago=44, status=InsuranceClaimStatus.PENDING),
        _claim(org, patient, insurance, days_ago=45, status=InsuranceClaimStatus.PENDING),
        _claim(org, patient, insurance, days_ago=60, status=InsuranceClaimStatus.INVOICED),
        _claim(org, patient, insurance, days_ago=90, status=InsuranceClaimStatus.COLLECTED),
    ])
    db_session.commit()

    alerts = DashboardAlertsService(db_session).get_alerts(org.id, claims_old_days=45)
    client = _client(db_session, user)
    try:
        listed = client.get("/api/v1/insurance-claims?min_days=45").json()
        assert listed["meta"]["total"] == alerts.old_insurance_claims.total_count == 2
    finally:
        app.dependency_overrides.clear()


def test_min_days_rejects_invalid_value(db_session: Session):
    _, user, _, _ = _org(db_session, "agebad")
    db_session.commit()
    client = _client(db_session, user)
    try:
        assert client.get("/api/v1/insurance-claims?min_days=30").status_code == 400
    finally:
        app.dependency_overrides.clear()
