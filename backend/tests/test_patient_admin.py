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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
    recent_ids = {p.id for p in summary.recent_payments}
    assert old_pending.id not in recent_ids
    assert old_pending.id in {item.payment_id for item in summary.pending_private_payments}
    assert summary.private_debt == Decimal("9000")
    assert len(summary.recent_payments) == 5


def test_pending_payment_without_appointment_appears(db_session: Session):
    org, _user, patient = _org(db_session, "priv-orphan")
    pending = _payment(org, patient, amount=Decimal("2500"), status=PaymentStatus.PENDING)
    db_session.add(pending)
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
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

    summary = PatientAdminService(db_session).get_admin_summary(org_a.id, patient_a.id)
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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient_a.id)
    assert summary.private_debt == Decimal("2000")
    ids = {item.payment_id for item in summary.pending_private_payments}
    assert pay_a.id in ids
    assert pay_b.id not in ids


def test_open_claims_pending_and_invoiced_appear_with_name(db_session: Session):
    org, _user, patient = _org(db_session, "os-open")
    insurance = _insurance(org, "OSDE")
    pending = _claim(org, patient, insurance, status=InsuranceClaimStatus.PENDING, amount=Decimal("3000"))
    invoiced = _claim(org, patient, insurance, status=InsuranceClaimStatus.INVOICED, amount=Decimal("5000"))
    db_session.add_all([insurance, pending, invoiced])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
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
    org, _user, patient = _org(db_session, "os-closed")
    insurance = _insurance(org, "Swiss")
    open_claim = _claim(org, patient, insurance, status=InsuranceClaimStatus.PENDING, amount=Decimal("1500"))
    collected = _claim(org, patient, insurance, status=InsuranceClaimStatus.COLLECTED, amount=Decimal("2000"))
    rejected = _claim(org, patient, insurance, status=InsuranceClaimStatus.REJECTED, amount=Decimal("2000"))
    db_session.add_all([insurance, open_claim, collected, rejected])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
    ids = {c.id for c in summary.pending_claims}
    assert open_claim.id in ids
    assert collected.id not in ids
    assert rejected.id not in ids
    assert summary.insurance_debt == Decimal("1500")


def test_open_claims_not_capped_at_ten(db_session: Session):
    org, _user, patient = _org(db_session, "os-many")
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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
    assert len(summary.pending_claims) == 11
    assert summary.insurance_debt == Decimal("11000")
    assert sum((c.expected_amount for c in summary.pending_claims), Decimal("0")) == summary.insurance_debt


def test_open_claims_isolates_other_organization(db_session: Session):
    org_a, _, patient_a = _org(db_session, "os-a")
    org_b, _, patient_b = _org(db_session, "os-b")
    ins_a = _insurance(org_a, "OSDE A")
    ins_b = _insurance(org_b, "OSDE B")
    claim_a = _claim(org_a, patient_a, ins_a, status=InsuranceClaimStatus.PENDING, amount=Decimal("1111"))
    claim_b = _claim(org_b, patient_b, ins_b, status=InsuranceClaimStatus.PENDING, amount=Decimal("9999"))
    db_session.add_all([ins_a, ins_b, claim_a, claim_b])
    db_session.commit()

    summary = PatientAdminService(db_session).get_admin_summary(org_a.id, patient_a.id)
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

    summary = PatientAdminService(db_session).get_admin_summary(org.id, patient.id)
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
