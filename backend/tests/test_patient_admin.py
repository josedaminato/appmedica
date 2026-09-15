"""GET /patients/{id}/admin-summary: detalle de deuda alineado con los totales."""

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
from app.services.patient_admin_service import PatientAdminService


NOW = datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc)


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


def _org(session: Session, slug: str) -> tuple[Organization, User, Patient]:
    org = Organization(
        id=uuid4(),
        name=f"Org {slug}",
        slug=slug,
        created_at=NOW,
        updated_at=NOW,
    )
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email=f"{slug}@test.com",
        full_name="Dra Test",
        password_hash="x",
        role=UserRole.OWNER,
        created_at=NOW,
        updated_at=NOW,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="García",
        dni=slug[:20],
        created_at=NOW,
        updated_at=NOW,
    )
    session.add_all([org, user, patient])
    session.flush()
    return org, user, patient


def _appt(org: Organization, patient: Patient, professional: User, *, start: datetime) -> Appointment:
    return Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=professional.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.PENDING,
        expected_amount=Decimal("10000"),
        created_at=NOW,
        updated_at=NOW,
    )


def _payment(
    org: Organization,
    patient: Patient,
    *,
    amount: Decimal,
    status: PaymentStatus,
    appointment: Appointment | None = None,
    professional: User | None = None,
    created_at: datetime = NOW,
) -> Payment:
    return Payment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        appointment_id=appointment.id if appointment else None,
        professional_id=professional.id if professional else None,
        amount=amount,
        method=PaymentMethod.CASH,
        status=status,
        paid_at=created_at if status == PaymentStatus.PAID else None,
        created_at=created_at,
        updated_at=created_at,
    )


def _insurance(org: Organization, name: str = "OSDE") -> HealthInsurance:
    return HealthInsurance(
        id=uuid4(),
        organization_id=org.id,
        name=name,
        created_at=NOW,
        updated_at=NOW,
    )


def _claim(
    org: Organization,
    patient: Patient,
    insurance: HealthInsurance,
    *,
    status: InsuranceClaimStatus,
    amount: Decimal = Decimal("8000"),
    service_date: date | None = None,
    appointment: Appointment | None = None,
) -> InsuranceClaim:
    return InsuranceClaim(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        appointment_id=appointment.id if appointment else None,
        health_insurance_id=insurance.id,
        expected_amount=amount,
        service_date=service_date or date(2026, 6, 1),
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def test_pending_payment_appears_and_matches_private_debt(db_session: Session):
    org, user, patient = _org(db_session, "priv-match")
    appt = _appt(org, patient, user, start=NOW - timedelta(days=2))
    pending = _payment(
        org, patient, amount=Decimal("4500"), status=PaymentStatus.PENDING,
        appointment=appt, professional=user,
    )
    db_session.add_all([appt, pending])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert summary.private_debt == Decimal("4500")
    assert len(summary.pending_private_payments) == 1
    item = summary.pending_private_payments[0]
    assert item.payment_id == pending.id
    assert item.appointment_id == appt.id
    assert item.amount == Decimal("4500")
    assert item.appointment_start_at == appt.start_at
    assert item.professional_name == user.full_name
    assert sum((p.amount for p in summary.pending_private_payments), Decimal("0")) == summary.private_debt


def test_paid_payment_does_not_appear_in_private_detail(db_session: Session):
    org, user, patient = _org(db_session, "priv-paid")
    db_session.add(_payment(org, patient, amount=Decimal("3000"), status=PaymentStatus.PAID, professional=user))
    db_session.add(_payment(org, patient, amount=Decimal("1200"), status=PaymentStatus.PENDING, professional=user))
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert summary.private_debt == Decimal("1200")
    ids = {item.payment_id for item in summary.pending_private_payments}
    assert len(ids) == 1
    assert summary.pending_private_payments[0].amount == Decimal("1200")


def test_old_pending_payment_appears_beyond_recent_payments(db_session: Session):
    org, user, patient = _org(db_session, "priv-old")
    old_pending = _payment(
        org, patient, amount=Decimal("9000"), status=PaymentStatus.PENDING,
        professional=user, created_at=NOW - timedelta(days=60),
    )
    db_session.add(old_pending)
    for i in range(5):
        db_session.add(
            _payment(
                org, patient, amount=Decimal("100"), status=PaymentStatus.PAID,
                professional=user, created_at=NOW - timedelta(days=i),
            ),
        )
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    recent_ids = {p.id for p in summary.recent_payments}
    assert old_pending.id not in recent_ids
    assert old_pending.id in {item.payment_id for item in summary.pending_private_payments}
    assert summary.private_debt == Decimal("9000")
    assert len(summary.recent_payments) == 5


def test_pending_payment_without_appointment_appears(db_session: Session):
    org, user, patient = _org(db_session, "priv-orphan")
    pending = _payment(org, patient, amount=Decimal("2500"), status=PaymentStatus.PENDING)
    db_session.add(pending)
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert len(summary.pending_private_payments) == 1
    item = summary.pending_private_payments[0]
    assert item.payment_id == pending.id
    assert item.appointment_id is None
    assert item.appointment_start_at is None
    assert summary.private_debt == Decimal("2500")


def test_private_debt_isolates_other_organization(db_session: Session):
    org_a, user_a, patient_a = _org(db_session, "org-a-priv")
    org_b, user_b, patient_b = _org(db_session, "org-b-priv")
    db_session.add(_payment(org_a, patient_a, amount=Decimal("1000"), status=PaymentStatus.PENDING, professional=user_a))
    db_session.add(_payment(org_b, patient_b, amount=Decimal("7000"), status=PaymentStatus.PENDING, professional=user_b))
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org_a.id, patient_a.id, user_a)
    assert summary.private_debt == Decimal("1000")
    assert len(summary.pending_private_payments) == 1
    assert summary.pending_private_payments[0].amount == Decimal("1000")


def test_private_debt_isolates_other_patient(db_session: Session):
    org, user, patient_a = _org(db_session, "pat-a")
    patient_b = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Luis",
        last_name="Otro",
        dni="30999111",
        created_at=NOW,
        updated_at=NOW,
    )
    pay_a = _payment(org, patient_a, amount=Decimal("2000"), status=PaymentStatus.PENDING, professional=user)
    pay_b = _payment(org, patient_b, amount=Decimal("4000"), status=PaymentStatus.PENDING, professional=user)
    db_session.add_all([patient_b, pay_a, pay_b])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient_a.id, user)
    assert summary.private_debt == Decimal("2000")
    ids = {item.payment_id for item in summary.pending_private_payments}
    assert pay_a.id in ids
    assert pay_b.id not in ids


def test_open_claims_pending_and_invoiced_appear_with_name(db_session: Session):
    org, user, patient = _org(db_session, "os-open")
    insurance = _insurance(org, "OSDE")
    pending = _claim(org, patient, insurance, status=InsuranceClaimStatus.PENDING, amount=Decimal("3000"))
    invoiced = _claim(org, patient, insurance, status=InsuranceClaimStatus.INVOICED, amount=Decimal("5000"))
    db_session.add_all([insurance, pending, invoiced])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert summary.insurance_debt == Decimal("8000")
    statuses = {c.status for c in summary.pending_claims}
    ids = {c.id for c in summary.pending_claims}
    assert pending.id in ids
    assert invoiced.id in ids
    assert InsuranceClaimStatus.PENDING in statuses
    assert InsuranceClaimStatus.INVOICED in statuses
    assert all(c.health_insurance_name == "OSDE" for c in summary.pending_claims)
    assert sum((c.expected_amount for c in summary.pending_claims), Decimal("0")) == summary.insurance_debt


def test_collected_and_rejected_claims_do_not_appear(db_session: Session):
    org, user, patient = _org(db_session, "os-closed")
    insurance = _insurance(org, "Swiss")
    open_claim = _claim(org, patient, insurance, status=InsuranceClaimStatus.PENDING, amount=Decimal("1500"))
    collected = _claim(org, patient, insurance, status=InsuranceClaimStatus.COLLECTED, amount=Decimal("2000"))
    rejected = _claim(org, patient, insurance, status=InsuranceClaimStatus.REJECTED, amount=Decimal("2000"))
    db_session.add_all([insurance, open_claim, collected, rejected])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    ids = {c.id for c in summary.pending_claims}
    assert open_claim.id in ids
    assert collected.id not in ids
    assert rejected.id not in ids
    assert summary.insurance_debt == Decimal("1500")


def test_open_claims_not_capped_at_ten(db_session: Session):
    org, user, patient = _org(db_session, "os-many")
    insurance = _insurance(org, "Galeno")
    db_session.add(insurance)
    for i in range(11):
        db_session.add(
            _claim(
                org, patient, insurance,
                status=InsuranceClaimStatus.PENDING,
                amount=Decimal("1000"),
                service_date=date(2026, 1, 1) + timedelta(days=i),
            ),
        )
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert len(summary.pending_claims) == 11
    assert summary.insurance_debt == Decimal("11000")
    assert sum((c.expected_amount for c in summary.pending_claims), Decimal("0")) == summary.insurance_debt


def test_open_claims_isolates_other_organization(db_session: Session):
    org_a, user_a, patient_a = _org(db_session, "os-a")
    org_b, _, patient_b = _org(db_session, "os-b")
    ins_a = _insurance(org_a, "OSDE A")
    ins_b = _insurance(org_b, "OSDE B")
    claim_a = _claim(org_a, patient_a, ins_a, status=InsuranceClaimStatus.PENDING, amount=Decimal("1111"))
    claim_b = _claim(org_b, patient_b, ins_b, status=InsuranceClaimStatus.PENDING, amount=Decimal("9999"))
    db_session.add_all([ins_a, ins_b, claim_a, claim_b])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org_a.id, patient_a.id, user_a)
    ids = {c.id for c in summary.pending_claims}
    assert claim_a.id in ids
    assert claim_b.id not in ids
    assert summary.insurance_debt == Decimal("1111")


def test_admin_summary_keeps_historial_and_timeline(db_session: Session):
    org, user, patient = _org(db_session, "hist")
    appt = _appt(org, patient, user, start=NOW - timedelta(days=1))
    paid = _payment(
        org, patient, amount=Decimal("1000"), status=PaymentStatus.PAID,
        appointment=appt, professional=user,
    )
    db_session.add_all([appt, paid])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id, user)
    assert summary.patient_id == patient.id
    assert summary.total_debt == summary.private_debt + summary.insurance_debt
    assert any(a.id == appt.id for a in summary.recent_appointments)
    assert any(p.id == paid.id for p in summary.recent_payments)
    event_types = {e.event_type for e in summary.timeline}
    assert "appointment" in event_types
    assert "payment" in event_types


def test_admin_summary_http_isolates_organization(db_session: Session):
    org_a, user_a, patient_a = _org(db_session, "http-a")
    org_b, user_b, patient_b = _org(db_session, "http-b")
    db_session.add(_payment(org_a, patient_a, amount=Decimal("2200"), status=PaymentStatus.PENDING, professional=user_a))
    db_session.add(_payment(org_b, patient_b, amount=Decimal("8800"), status=PaymentStatus.PENDING, professional=user_b))
    db_session.commit()

    def override_db():
        yield db_session

    def override_user():
        return user_a

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app, raise_server_exceptions=True)
    try:
        resp = client.get(f"/api/v1/patients/{patient_a.id}/admin-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert float(body["private_debt"]) == 2200.0
        assert len(body["pending_private_payments"]) == 1
        assert body["pending_private_payments"][0]["amount"] == "2200.00" or float(
            body["pending_private_payments"][0]["amount"],
        ) == 2200.0
        assert "pending_claims" in body
        assert "recent_payments" in body
        assert "recent_appointments" in body
        assert "timeline" in body

        foreign = client.get(f"/api/v1/patients/{patient_b.id}/admin-summary")
        assert foreign.status_code == 404
    finally:
        app.dependency_overrides.clear()


def _member(session: Session, org: Organization, *, email: str, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        organization_id=org.id,
        email=email,
        full_name=name,
        password_hash="x",
        role=role,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(user)
    session.flush()
    return user


def _http_client(db_session: Session, user: User) -> TestClient:
    def override_db():
        yield db_session

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app, raise_server_exceptions=True)


def _seed_shared_patient_ab(db_session: Session):
    org, owner, patient = _org(db_session, "scope-ab")
    staff = _member(db_session, org, email="staff-ab@test.com", name="Staff", role=UserRole.STAFF)
    prof_a = _member(db_session, org, email="profa-ab@test.com", name="Prof A", role=UserRole.PROFESSIONAL)
    prof_b = _member(db_session, org, email="profb-ab@test.com", name="Prof B", role=UserRole.PROFESSIONAL)
    prof_c = _member(db_session, org, email="profc-ab@test.com", name="Prof C", role=UserRole.PROFESSIONAL)
    insurance = _insurance(org, "OSDE AB")

    live_now = datetime.now(timezone.utc)
    appt_a = _appt(org, patient, prof_a, start=NOW - timedelta(days=2))
    appt_b = _appt(org, patient, prof_b, start=NOW - timedelta(days=1))
    upcoming_a = _appt(org, patient, prof_a, start=live_now + timedelta(days=7))
    upcoming_a.status = AppointmentStatus.PENDING
    upcoming_a.closure_status = AppointmentClosureStatus.NONE
    no_show_b = _appt(org, patient, prof_b, start=live_now - timedelta(days=3))
    no_show_b.status = AppointmentStatus.NO_SHOW
    no_show_b.closure_status = AppointmentClosureStatus.NONE

    pay_a_pending = _payment(
        org, patient, amount=Decimal("4000"), status=PaymentStatus.PENDING,
        appointment=appt_a, professional=prof_a,
    )
    pay_b_pending = _payment(
        org, patient, amount=Decimal("7000"), status=PaymentStatus.PENDING,
        appointment=appt_b, professional=prof_b,
    )
    pay_a_paid = _payment(
        org, patient, amount=Decimal("1500"), status=PaymentStatus.PAID,
        appointment=appt_a, professional=prof_a,
    )
    pay_b_paid = _payment(
        org, patient, amount=Decimal("2500"), status=PaymentStatus.PAID,
        appointment=appt_b, professional=prof_b,
    )
    claim_a = _claim(
        org, patient, insurance, status=InsuranceClaimStatus.PENDING,
        amount=Decimal("3000"), appointment=appt_a,
    )
    claim_b = _claim(
        org, patient, insurance, status=InsuranceClaimStatus.INVOICED,
        amount=Decimal("9000"), appointment=appt_b,
    )
    orphan = _claim(
        org, patient, insurance, status=InsuranceClaimStatus.PENDING,
        amount=Decimal("111"), appointment=None,
    )
    db_session.add_all([
        insurance, appt_a, appt_b, upcoming_a, no_show_b,
        pay_a_pending, pay_b_pending, pay_a_paid, pay_b_paid,
        claim_a, claim_b, orphan,
    ])
    db_session.commit()
    return {
        "org": org, "owner": owner, "staff": staff, "patient": patient,
        "prof_a": prof_a, "prof_b": prof_b, "prof_c": prof_c,
        "appt_a": appt_a, "appt_b": appt_b, "upcoming_a": upcoming_a, "no_show_b": no_show_b,
        "pay_a_pending": pay_a_pending, "pay_b_pending": pay_b_pending,
        "pay_a_paid": pay_a_paid, "pay_b_paid": pay_b_paid,
        "claim_a": claim_a, "claim_b": claim_b, "orphan": orphan,
    }


def _assert_professional_a_scope(body: dict, seeded: dict) -> None:
    appt_ids = {row["id"] for row in body["recent_appointments"]}
    upcoming_ids = {row["id"] for row in body["upcoming_appointments"]}
    pending_pay_ids = {row["payment_id"] for row in body["pending_private_payments"]}
    recent_pay_ids = {row["id"] for row in body["recent_payments"]}
    claim_ids = {row["id"] for row in body["pending_claims"]}
    timeline_ids = {row["id"] for row in body["timeline"]}

    assert str(seeded["appt_a"].id) in appt_ids
    assert str(seeded["appt_b"].id) not in appt_ids
    assert str(seeded["upcoming_a"].id) in upcoming_ids
    assert str(seeded["pay_a_pending"].id) in pending_pay_ids
    assert str(seeded["pay_b_pending"].id) not in pending_pay_ids
    assert str(seeded["pay_a_paid"].id) in recent_pay_ids
    assert str(seeded["pay_b_paid"].id) not in recent_pay_ids
    assert str(seeded["claim_a"].id) in claim_ids
    assert str(seeded["claim_b"].id) not in claim_ids
    assert str(seeded["orphan"].id) not in claim_ids
    assert float(body["private_debt"]) == 4000.0
    assert float(body["insurance_debt"]) == 3000.0
    assert body["no_show_count"] == 0
    assert body["no_shows_last_30_days"] == 0
    assert str(seeded["appt_b"].id) not in timeline_ids
    assert str(seeded["pay_b_pending"].id) not in timeline_ids
    assert str(seeded["pay_b_paid"].id) not in timeline_ids
    assert str(seeded["claim_b"].id) not in timeline_ids
    assert str(seeded["no_show_b"].id) not in timeline_ids
    assert str(seeded["orphan"].id) not in timeline_ids


def test_admin_summary_professional_a_does_not_see_professional_b(db_session: Session):
    seeded = _seed_shared_patient_ab(db_session)
    client = _http_client(db_session, seeded["prof_a"])
    try:
        resp = client.get(f"/api/v1/patients/{seeded['patient'].id}/admin-summary")
        assert resp.status_code == 200, resp.text
        _assert_professional_a_scope(resp.json(), seeded)
        denied = client.get(f"/api/v1/insurance-claims/{seeded['claim_b'].id}")
        assert denied.status_code == 403, denied.text
        claim_ids = {row["id"] for row in resp.json()["pending_claims"]}
        assert str(seeded["claim_b"].id) not in claim_ids
    finally:
        app.dependency_overrides.clear()


def test_admin_summary_professional_b_does_not_see_professional_a(db_session: Session):
    seeded = _seed_shared_patient_ab(db_session)
    client = _http_client(db_session, seeded["prof_b"])
    try:
        resp = client.get(f"/api/v1/patients/{seeded['patient'].id}/admin-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        appt_ids = {row["id"] for row in body["recent_appointments"]}
        pending_pay_ids = {row["payment_id"] for row in body["pending_private_payments"]}
        recent_pay_ids = {row["id"] for row in body["recent_payments"]}
        claim_ids = {row["id"] for row in body["pending_claims"]}
        timeline_ids = {row["id"] for row in body["timeline"]}
        assert str(seeded["appt_b"].id) in appt_ids
        assert str(seeded["appt_a"].id) not in appt_ids
        assert str(seeded["pay_b_pending"].id) in pending_pay_ids
        assert str(seeded["pay_a_pending"].id) not in pending_pay_ids
        assert str(seeded["pay_b_paid"].id) in recent_pay_ids
        assert str(seeded["pay_a_paid"].id) not in recent_pay_ids
        assert str(seeded["claim_b"].id) in claim_ids
        assert str(seeded["claim_a"].id) not in claim_ids
        assert float(body["private_debt"]) == 7000.0
        assert float(body["insurance_debt"]) == 9000.0
        assert body["no_show_count"] == 1
        assert body["no_shows_last_30_days"] == 1
        assert str(seeded["appt_a"].id) not in timeline_ids
        assert str(seeded["pay_a_pending"].id) not in timeline_ids
        assert str(seeded["claim_a"].id) not in timeline_ids
        assert str(seeded["orphan"].id) not in claim_ids
        assert client.get(f"/api/v1/insurance-claims/{seeded['claim_a'].id}").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_summary_professional_without_activity_is_empty_200(db_session: Session):
    seeded = _seed_shared_patient_ab(db_session)
    client = _http_client(db_session, seeded["prof_c"])
    try:
        resp = client.get(f"/api/v1/patients/{seeded['patient'].id}/admin-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert float(body["private_debt"]) == 0.0
        assert float(body["insurance_debt"]) == 0.0
        assert float(body["total_debt"]) == 0.0
        assert body["no_show_count"] == 0
        assert body["no_shows_last_30_days"] == 0
        assert body["upcoming_appointments"] == []
        assert body["recent_appointments"] == []
        assert body["recent_payments"] == []
        assert body["pending_private_payments"] == []
        assert body["pending_claims"] == []
        assert body["timeline"] == []
    finally:
        app.dependency_overrides.clear()


def test_admin_summary_owner_sees_both_professionals(db_session: Session):
    seeded = _seed_shared_patient_ab(db_session)
    client = _http_client(db_session, seeded["owner"])
    try:
        resp = client.get(f"/api/v1/patients/{seeded['patient'].id}/admin-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        appt_ids = {row["id"] for row in body["recent_appointments"]}
        claim_ids = {row["id"] for row in body["pending_claims"]}
        pending_pay_ids = {row["payment_id"] for row in body["pending_private_payments"]}
        timeline_ids = {row["id"] for row in body["timeline"]}
        assert str(seeded["appt_a"].id) in appt_ids
        assert str(seeded["appt_b"].id) in appt_ids
        assert str(seeded["pay_a_pending"].id) in pending_pay_ids
        assert str(seeded["pay_b_pending"].id) in pending_pay_ids
        assert str(seeded["claim_a"].id) in claim_ids
        assert str(seeded["claim_b"].id) in claim_ids
        assert str(seeded["orphan"].id) in claim_ids
        assert float(body["private_debt"]) == 11000.0
        assert float(body["insurance_debt"]) == 12111.0
        assert body["no_show_count"] == 1
        assert str(seeded["appt_a"].id) in timeline_ids
        assert str(seeded["appt_b"].id) in timeline_ids
    finally:
        app.dependency_overrides.clear()


def test_admin_summary_staff_sees_both_professionals(db_session: Session):
    seeded = _seed_shared_patient_ab(db_session)
    client = _http_client(db_session, seeded["staff"])
    try:
        resp = client.get(f"/api/v1/patients/{seeded['patient'].id}/admin-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        appt_ids = {row["id"] for row in body["recent_appointments"]}
        claim_ids = {row["id"] for row in body["pending_claims"]}
        assert str(seeded["appt_a"].id) in appt_ids
        assert str(seeded["appt_b"].id) in appt_ids
        assert str(seeded["claim_a"].id) in claim_ids
        assert str(seeded["claim_b"].id) in claim_ids
        assert str(seeded["orphan"].id) in claim_ids
        assert float(body["private_debt"]) == 11000.0
        assert float(body["insurance_debt"]) == 12111.0
        assert body["no_show_count"] == 1
    finally:
        app.dependency_overrides.clear()

