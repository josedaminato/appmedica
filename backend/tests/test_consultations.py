"""Tests de consultas clínicas e historia clínica."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    ConsultationStatus,
    UserRole,
)
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.user import User
from app.models.health_insurance import HealthInsurance


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
        Consultation.__table__,
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


def _seed_two_pros(db_session: Session) -> dict:
    now = datetime.now(timezone.utc)
    org = Organization(id=uuid4(), name="Consultas Org", slug="consultas-org")
    owner = User(
        id=uuid4(), organization_id=org.id, email="owner@consultas.example.com",
        full_name="Dr Owner", password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
    )
    prof_a = User(
        id=uuid4(), organization_id=org.id, email="profa@consultas.example.com",
        full_name="Dr A", password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(), organization_id=org.id, email="profb@consultas.example.com",
        full_name="Dr B", password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    patient = Patient(
        id=uuid4(), organization_id=org.id,
        first_name="Juan", last_name="Pérez", dni="40111222",
    )
    appt_a = Appointment(
        id=uuid4(), organization_id=org.id, patient_id=patient.id,
        professional_id=prof_a.id, start_at=now, end_at=now + timedelta(hours=1),
        status=AppointmentStatus.ATTENDED, modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE, closure_status=AppointmentClosureStatus.NONE,
    )
    appt_b = Appointment(
        id=uuid4(), organization_id=org.id, patient_id=patient.id,
        professional_id=prof_b.id, start_at=now - timedelta(days=1),
        end_at=now - timedelta(hours=23), status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON, attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db_session.add_all([org, owner, prof_a, prof_b, patient, appt_a, appt_b])
    db_session.commit()
    return {
        "org": org, "owner": owner, "prof_a": prof_a, "prof_b": prof_b,
        "patient": patient, "appt_a": appt_a, "appt_b": appt_b,
        "password": "TestPass123!",
    }


@pytest.fixture()
def api_client(db_session: Session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    previous_limiter_enabled = limiter.enabled
    limiter.enabled = False

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client
    finally:
        limiter.enabled = previous_limiter_enabled
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _auth(client: TestClient, user: User, password: str = "TestPass123!") -> dict:
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_api_datetime(value: str) -> datetime:
    return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def test_create_consultation_for_attended_appointment(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])

    resp = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["appointment_id"] == str(data["appt_a"].id)
    assert body["patient_id"] == str(data["patient"].id)
    assert body["professional_id"] == str(data["prof_a"].id)
    assert body["created_by"] == str(data["owner"].id)
    assert body["amends_id"] is None
    assert body["amend_reason"] is None
    assert body["occurred_at"] is not None
    created_occurred = _parse_api_datetime(body["occurred_at"])
    assert created_occurred == _as_utc(data["appt_a"].start_at)

    fetched = api_client.get(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    by_id = api_client.get(f"/api/v1/consultations/{body['id']}", headers=headers)
    assert by_id.status_code == 200
    assert by_id.json()["status"] == "draft"

    dup = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert dup.status_code == 409


def test_professional_cannot_create_consultation_for_other_appointment(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.post(
        f"/api/v1/appointments/{data['appt_b'].id}/consultation",
        headers=headers,
    )
    assert resp.status_code == 403


def test_update_draft_and_finalize(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])

    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).json()
    cid = created["id"]

    bad_finalize = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert bad_finalize.status_code == 400

    patch = api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Dolor lumbar", "evolution": "Paciente refiere dolor mecánico"},
    )
    assert patch.status_code == 200
    assert patch.json()["reason"] == "Dolor lumbar"

    api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"diagnosis": "Lumbalgia"},
    )
    fin = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert fin.status_code == 200
    assert fin.json()["status"] == "finalized"

    locked = api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Otro"},
    )
    assert locked.status_code == 400


def test_finalize_does_not_create_payment_or_change_closure(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])

    cid = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).json()["id"]
    api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Control", "evolution": "Estable"},
    )
    api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)

    appt = db_session.get(Appointment, data["appt_a"].id)
    assert appt.closure_status == AppointmentClosureStatus.NONE
    payments = db_session.query(Payment).filter(Payment.appointment_id == appt.id).all()
    assert payments == []


def test_org_isolation(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers_a = _auth(api_client, data["owner"], data["password"])

    cid = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers_a,
    ).json()["id"]

    org2 = Organization(id=uuid4(), name="Otra", slug="otra-consultas")
    user2 = User(
        id=uuid4(), organization_id=org2.id, email="otro@consultas.example.com",
        full_name="Otro", password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
    )
    db_session.add_all([org2, user2])
    db_session.commit()
    headers_b = _auth(api_client, user2)

    assert api_client.get(f"/api/v1/consultations/{cid}", headers=headers_b).status_code == 404
    assert api_client.get(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers_b,
    ).status_code == 404
    assert api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers_b,
    ).status_code == 404
    assert api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers_b,
        json={},
    ).status_code == 404


def test_list_patient_consultations_scoped_for_professional(api_client, db_session):
    data = _seed_two_pros(db_session)
    owner_h = _auth(api_client, data["owner"], data["password"])
    a_h = _auth(api_client, data["prof_a"])

    api_client.post(f"/api/v1/appointments/{data['appt_a'].id}/consultation", headers=owner_h)
    api_client.post(f"/api/v1/appointments/{data['appt_b'].id}/consultation", headers=owner_h)

    owner_list = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=owner_h,
    ).json()
    assert len(owner_list) == 2

    prof_a_list = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=a_h,
    ).json()
    assert len(prof_a_list) == 1
    assert prof_a_list[0]["professional_id"] == str(data["prof_a"].id)


def test_staff_blocked_from_clinical(api_client, db_session):
    data = _seed_two_pros(db_session)
    staff = User(
        id=uuid4(), organization_id=data["org"].id, email="staff@consultas.example.com",
        full_name="Staff", password_hash=hash_password("TestPass123!"),
        role=UserRole.STAFF,
    )
    db_session.add(staff)
    db_session.commit()
    headers = _auth(api_client, staff)

    assert api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).status_code == 403

    assert api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
    ).status_code == 403

    assert api_client.get(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).status_code == 403

    assert api_client.get(
        f"/api/v1/patients/{data['patient'].id}/clinical",
        headers=headers,
    ).status_code == 403

    assert api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={},
    ).status_code == 403
    assert api_client.post(
        f"/api/v1/consultations/{data['appt_a'].id}/amendments",
        headers=headers,
        json={"amend_reason": "No corresponde"},
    ).status_code == 403


def test_patient_clinical_profile(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])

    patch = api_client.patch(
        f"/api/v1/patients/{data['patient'].id}/clinical",
        headers=headers,
        json={"allergies": "Penicilina", "medical_history": "HTA"},
    )
    assert patch.status_code == 200
    assert patch.json()["allergies"] == "Penicilina"
    assert patch.json()["clinical_updated_by"] == str(data["prof_a"].id)
    assert patch.json()["clinical_updated_by_name"] == "Dr A"
    assert patch.json()["clinical_updated_at"] is not None

    get = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/clinical",
        headers=headers,
    )
    assert get.status_code == 200
    assert get.json()["medical_history"] == "HTA"
    assert get.json()["clinical_updated_by"] == str(data["prof_a"].id)
    assert get.json()["clinical_updated_by_name"] == "Dr A"
    assert get.json()["clinical_updated_at"] is not None


def test_clinical_profile_partial_patch_keeps_other_fields(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient"].id

    first = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"allergies": "Penicilina", "medical_history": "HTA"},
    )
    assert first.status_code == 200
    first_at = first.json()["clinical_updated_at"]

    second = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"allergies": "Polen"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["allergies"] == "Polen"
    assert body["medical_history"] == "HTA"
    assert body["current_medications"] is None
    assert body["clinical_updated_by"] == str(data["prof_a"].id)
    assert body["clinical_updated_at"] != first_at


def test_clinical_profile_empty_patch_does_not_change_attribution(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient"].id

    first = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"allergies": "Penicilina"},
    )
    assert first.status_code == 200
    first_body = first.json()

    empty = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={},
    )
    assert empty.status_code == 200
    assert empty.json()["allergies"] == "Penicilina"
    assert empty.json()["clinical_updated_by"] == first_body["clinical_updated_by"]
    assert empty.json()["clinical_updated_at"] == first_body["clinical_updated_at"]


def test_cannot_create_consultation_if_appointment_not_attended(api_client, db_session):
    data = _seed_two_pros(db_session)
    now = datetime.now(timezone.utc)
    pending = Appointment(
        id=uuid4(), organization_id=data["org"].id, patient_id=data["patient"].id,
        professional_id=data["prof_a"].id, start_at=now, end_at=now + timedelta(hours=1),
        status=AppointmentStatus.PENDING, modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE, closure_status=AppointmentClosureStatus.NONE,
    )
    db_session.add(pending)
    db_session.commit()
    headers = _auth(api_client, data["owner"], data["password"])

    resp = api_client.post(
        f"/api/v1/appointments/{pending.id}/consultation",
        headers=headers,
    )
    assert resp.status_code == 400


def test_cannot_create_consultation_without_professional(api_client, db_session):
    data = _seed_two_pros(db_session)
    now = datetime.now(timezone.utc)
    unassigned = Appointment(
        id=uuid4(), organization_id=data["org"].id, patient_id=data["patient"].id,
        professional_id=None, start_at=now, end_at=now + timedelta(hours=1),
        status=AppointmentStatus.ATTENDED, modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE, closure_status=AppointmentClosureStatus.NONE,
    )
    db_session.add(unassigned)
    db_session.commit()
    headers = _auth(api_client, data["owner"], data["password"])

    resp = api_client.post(
        f"/api/v1/appointments/{unassigned.id}/consultation",
        headers=headers,
    )
    assert resp.status_code == 400


def test_clinical_unknown_patient_returns_404(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])
    missing = uuid4()

    assert api_client.get(
        f"/api/v1/patients/{missing}/clinical",
        headers=headers,
    ).status_code == 404
    assert api_client.patch(
        f"/api/v1/patients/{missing}/clinical",
        headers=headers,
        json={"allergies": "X"},
    ).status_code == 404
    assert api_client.get(
        f"/api/v1/patients/{missing}/consultations",
        headers=headers,
    ).status_code == 404


def test_unknown_appointment_and_consultation_return_404(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])
    missing = uuid4()

    assert api_client.get(
        f"/api/v1/appointments/{missing}/consultation",
        headers=headers,
    ).status_code == 404
    assert api_client.post(
        f"/api/v1/appointments/{missing}/consultation",
        headers=headers,
    ).status_code == 404
    assert api_client.get(f"/api/v1/consultations/{missing}", headers=headers).status_code == 404
    assert api_client.patch(
        f"/api/v1/consultations/{missing}",
        headers=headers,
        json={"reason": "X"},
    ).status_code == 404


def test_staff_cannot_get_patch_or_finalize_consultation_by_id(api_client, db_session):
    data = _seed_two_pros(db_session)
    owner_h = _auth(api_client, data["owner"], data["password"])
    cid = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=owner_h,
    ).json()["id"]

    staff = User(
        id=uuid4(), organization_id=data["org"].id, email="staff2@consultas.example.com",
        full_name="Staff 2", password_hash=hash_password("TestPass123!"),
        role=UserRole.STAFF,
    )
    db_session.add(staff)
    db_session.commit()
    staff_h = _auth(api_client, staff)

    assert api_client.get(f"/api/v1/consultations/{cid}", headers=staff_h).status_code == 403
    assert api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=staff_h,
        json={"reason": "Hack"},
    ).status_code == 403
    assert api_client.post(
        f"/api/v1/consultations/{cid}/finalize",
        headers=staff_h,
    ).status_code == 403


def test_professional_cannot_get_colleague_consultation_by_id(api_client, db_session):
    data = _seed_two_pros(db_session)
    owner_h = _auth(api_client, data["owner"], data["password"])
    cid_b = api_client.post(
        f"/api/v1/appointments/{data['appt_b'].id}/consultation",
        headers=owner_h,
    ).json()["id"]

    a_h = _auth(api_client, data["prof_a"])
    assert api_client.get(f"/api/v1/consultations/{cid_b}", headers=a_h).status_code == 403
    assert api_client.patch(
        f"/api/v1/consultations/{cid_b}",
        headers=a_h,
        json={"reason": "Hack"},
    ).status_code == 403
    assert api_client.post(
        f"/api/v1/consultations/{cid_b}/finalize",
        headers=a_h,
    ).status_code == 403
    assert api_client.get(
        f"/api/v1/appointments/{data['appt_b'].id}/consultation",
        headers=a_h,
    ).status_code == 403


def test_finalize_rejects_whitespace_only_fields(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    cid = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).json()["id"]
    api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "   ", "evolution": "   "},
    )
    resp = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert resp.status_code == 400


def test_finalize_snapshots_professional_identity_independent_of_later_rename(
    api_client, db_session,
):
    data = _seed_two_pros(db_session)
    prof = data["prof_a"]
    prof.full_name = "Dr. Juan Pérez"
    prof.license_number = "MN 12345"
    db_session.commit()
    headers = _auth(api_client, prof)

    cid = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).json()["id"]
    draft = api_client.get(f"/api/v1/consultations/{cid}", headers=headers).json()
    assert draft["status"] == "draft"
    assert draft["professional_name"] == "Dr. Juan Pérez"
    assert draft["professional_name_snapshot"] is None
    assert draft["professional_license_snapshot"] is None

    api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Control", "evolution": "Estable"},
    )
    fin = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert fin.status_code == 200
    body = fin.json()
    assert body["status"] == "finalized"
    assert body["professional_name_snapshot"] == "Dr. Juan Pérez"
    assert body["professional_license_snapshot"] == "MN 12345"
    assert body["professional_name"] == "Dr. Juan Pérez"

    prof.full_name = "Dr. Juan Pérez Gómez"
    prof.license_number = "MN 99999"
    db_session.commit()

    stored = db_session.get(Consultation, UUID(cid))
    db_session.refresh(stored)
    assert stored.professional_name_snapshot == "Dr. Juan Pérez"
    assert stored.professional_license_snapshot == "MN 12345"

    got = api_client.get(f"/api/v1/consultations/{cid}", headers=headers).json()
    assert got["professional_name"] == "Dr. Juan Pérez"
    assert got["professional_name_snapshot"] == "Dr. Juan Pérez"
    assert got["professional_license_snapshot"] == "MN 12345"

    now = datetime.now(timezone.utc)
    appt_draft = Appointment(
        id=uuid4(), organization_id=data["org"].id, patient_id=data["patient"].id,
        professional_id=prof.id, start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, hours=1), status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON, attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db_session.add(appt_draft)
    db_session.commit()

    draft_created = api_client.post(
        f"/api/v1/appointments/{appt_draft.id}/consultation",
        headers=headers,
    )
    assert draft_created.status_code == 201
    draft_body = draft_created.json()
    assert draft_body["status"] == "draft"
    assert draft_body["professional_name"] == "Dr. Juan Pérez Gómez"
    assert draft_body["professional_name_snapshot"] is None

    listed = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
    ).json()
    by_id = {item["id"]: item for item in listed}
    assert by_id[cid]["professional_name"] == "Dr. Juan Pérez"
    assert by_id[draft_body["id"]]["professional_name"] == "Dr. Juan Pérez Gómez"


def test_create_standalone_consultation_without_appointment(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    occurred = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)

    resp = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={"occurred_at": occurred.isoformat()},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["appointment_id"] is None
    assert body["amends_id"] is None
    assert body["amend_reason"] is None
    assert body["patient_id"] == str(data["patient"].id)
    assert body["professional_id"] == str(data["prof_a"].id)
    assert body["created_by"] == str(data["prof_a"].id)
    assert body["status"] == "draft"
    stored_occurred = _parse_api_datetime(body["occurred_at"])
    assert stored_occurred == occurred


def test_standalone_consultation_defaults_occurred_at_to_now(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])
    before = datetime.now(timezone.utc)

    resp = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["appointment_id"] is None
    stored = _parse_api_datetime(body["occurred_at"])
    after = datetime.now(timezone.utc)
    assert before - timedelta(seconds=5) <= stored <= after + timedelta(seconds=5)


def test_standalone_consultation_accepts_occurred_at_older_than_thirty_days(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    past = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=90)

    resp = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={"occurred_at": past.isoformat()},
    )
    assert resp.status_code == 201
    stored = _parse_api_datetime(resp.json()["occurred_at"])
    assert stored == _as_utc(past)


def test_list_patient_consultations_includes_notes_and_amendments_ordered(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])

    older = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={"occurred_at": "2026-01-01T10:00:00+00:00"},
    )
    assert older.status_code == 201
    visit = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert visit.status_code == 201
    primary = db_session.get(Consultation, UUID(visit.json()["id"]))
    amendment = Consultation(
        organization_id=data["org"].id,
        appointment_id=data["appt_a"].id,
        patient_id=data["patient"].id,
        professional_id=data["prof_a"].id,
        amends_id=primary.id,
        amend_reason="Corrección de diagnóstico",
        occurred_at=data["appt_a"].start_at + timedelta(hours=2),
        status=ConsultationStatus.DRAFT,
        created_by=data["owner"].id,
    )
    db_session.add(amendment)
    db_session.commit()

    listed = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
    )
    assert listed.status_code == 200
    items = listed.json()
    assert [item["id"] for item in items] == [
        str(amendment.id),
        visit.json()["id"],
        older.json()["id"],
    ]
    by_id = {item["id"]: item for item in items}
    assert by_id[older.json()["id"]]["appointment_id"] is None
    assert by_id[visit.json()["id"]]["amends_id"] is None
    assert by_id[str(amendment.id)]["amends_id"] == visit.json()["id"]
    assert by_id[str(amendment.id)]["amend_reason"] == "Corrección de diagnóstico"


def test_get_appointment_consultation_returns_primary_not_amendment(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])

    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert created.status_code == 201
    primary_id = created.json()["id"]
    primary = db_session.get(Consultation, UUID(primary_id))
    amendment = Consultation(
        organization_id=data["org"].id,
        appointment_id=data["appt_a"].id,
        patient_id=data["patient"].id,
        professional_id=data["prof_a"].id,
        amends_id=primary.id,
        amend_reason="Corrección de indicaciones",
        occurred_at=data["appt_a"].start_at,
        status=ConsultationStatus.DRAFT,
        created_by=data["owner"].id,
    )
    db_session.add(amendment)
    db_session.commit()

    fetched = api_client.get(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == primary_id
    assert fetched.json()["amends_id"] is None
    assert fetched.json()["id"] != str(amendment.id)


def test_amendment_without_reason_is_rejected(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    primary = db_session.get(Consultation, UUID(created.json()["id"]))
    db_session.add(
        Consultation(
            organization_id=data["org"].id,
            appointment_id=data["appt_a"].id,
            patient_id=data["patient"].id,
            professional_id=data["prof_a"].id,
            amends_id=primary.id,
            amend_reason=None,
            status=ConsultationStatus.DRAFT,
            created_by=data["owner"].id,
        ),
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_orm_allows_amendment_with_same_appointment_as_primary(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["owner"], data["password"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    primary = db_session.get(Consultation, UUID(created.json()["id"]))
    amendment = Consultation(
        organization_id=data["org"].id,
        appointment_id=data["appt_a"].id,
        patient_id=data["patient"].id,
        professional_id=data["prof_a"].id,
        amends_id=primary.id,
        amend_reason="Error de tipeo en evolución",
        occurred_at=data["appt_a"].start_at,
        status=ConsultationStatus.DRAFT,
        created_by=data["owner"].id,
    )
    db_session.add(amendment)
    db_session.commit()
    db_session.refresh(amendment)
    assert amendment.appointment_id == data["appt_a"].id
    assert amendment.amends_id == primary.id


def test_finalize_standalone_consultation(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    created = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=headers,
        json={},
    )
    assert created.status_code == 201
    cid = created.json()["id"]
    api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Control telefónico", "evolution": "Paciente estable"},
    )
    fin = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert fin.status_code == 200
    assert fin.json()["status"] == "finalized"
    locked = api_client.patch(
        f"/api/v1/consultations/{cid}",
        headers=headers,
        json={"reason": "Otro"},
    )
    assert locked.status_code == 400
    again = api_client.post(f"/api/v1/consultations/{cid}/finalize", headers=headers)
    assert again.status_code == 400


def _finalize(client: TestClient, headers: dict, consultation_id: str) -> dict:
    patch = client.patch(
        f"/api/v1/consultations/{consultation_id}",
        headers=headers,
        json={"reason": "Motivo clínico", "evolution": "Evolución clínica"},
    )
    assert patch.status_code == 200, patch.text
    fin = client.post(f"/api/v1/consultations/{consultation_id}/finalize", headers=headers)
    assert fin.status_code == 200, fin.text
    return fin.json()


def test_cannot_amend_draft_consultation(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    resp = api_client.post(
        f"/api/v1/consultations/{created.json()['id']}/amendments",
        headers=headers,
        json={"amend_reason": "Intento prematuro"},
    )
    assert resp.status_code == 400


def test_amend_finalized_creates_new_row_pointing_to_original(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    original = _finalize(api_client, headers, created.json()["id"])
    original_id = original["id"]

    missing_reason = api_client.post(
        f"/api/v1/consultations/{original_id}/amendments",
        headers=headers,
        json={"amend_reason": "   "},
    )
    assert missing_reason.status_code == 400

    amendment = api_client.post(
        f"/api/v1/consultations/{original_id}/amendments",
        headers=headers,
        json={"amend_reason": "Corrección de diagnóstico"},
    )
    assert amendment.status_code == 201
    body = amendment.json()
    assert body["id"] != original_id
    assert body["amends_id"] == original_id
    assert body["amend_reason"] == "Corrección de diagnóstico"
    assert body["appointment_id"] == str(data["appt_a"].id)
    assert body["patient_id"] == original["patient_id"]
    assert body["status"] == "draft"
    assert body["professional_id"] == str(data["prof_a"].id)
    assert body["reason"] is None
    assert _parse_api_datetime(body["occurred_at"]) == _parse_api_datetime(original["occurred_at"])

    stored_original = api_client.get(
        f"/api/v1/consultations/{original_id}",
        headers=headers,
    ).json()
    assert stored_original["status"] == "finalized"
    assert stored_original["reason"] == "Motivo clínico"
    assert stored_original["amends_id"] is None

    primary = api_client.get(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    ).json()
    assert primary["id"] == original_id


def test_amendment_of_amendment_points_to_original(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    original = _finalize(api_client, headers, created.json()["id"])
    first = api_client.post(
        f"/api/v1/consultations/{original['id']}/amendments",
        headers=headers,
        json={"amend_reason": "Primera corrección"},
    ).json()
    first_final = _finalize(api_client, headers, first["id"])
    second = api_client.post(
        f"/api/v1/consultations/{first_final['id']}/amendments",
        headers=headers,
        json={"amend_reason": "Segunda corrección"},
    )
    assert second.status_code == 201
    assert second.json()["amends_id"] == original["id"]
    assert second.json()["amends_id"] != first["id"]


def test_amendment_cross_org_is_404(api_client, db_session):
    data = _seed_two_pros(db_session)
    headers = _auth(api_client, data["prof_a"])
    created = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=headers,
    )
    original = _finalize(api_client, headers, created.json()["id"])
    org2 = Organization(id=uuid4(), name="Otra 2", slug="otra-consultas-2")
    user2 = User(
        id=uuid4(), organization_id=org2.id, email="otro2@consultas.example.com",
        full_name="Otro 2", password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
    )
    db_session.add_all([org2, user2])
    db_session.commit()
    other = _auth(api_client, user2)
    assert api_client.post(
        f"/api/v1/consultations/{original['id']}/amendments",
        headers=other,
        json={"amend_reason": "Cross org"},
    ).status_code == 404


def test_professional_sees_colleague_finalized_but_not_draft(api_client, db_session):
    data = _seed_two_pros(db_session)
    owner_h = _auth(api_client, data["owner"], data["password"])
    a_h = _auth(api_client, data["prof_a"])
    b_h = _auth(api_client, data["prof_b"])

    own_draft = api_client.post(
        f"/api/v1/appointments/{data['appt_a'].id}/consultation",
        headers=a_h,
    ).json()
    colleague = api_client.post(
        f"/api/v1/appointments/{data['appt_b'].id}/consultation",
        headers=b_h,
    ).json()

    listed_drafts = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=a_h,
    ).json()
    assert {item["id"] for item in listed_drafts} == {own_draft["id"]}

    _finalize(api_client, b_h, colleague["id"])
    listed = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=a_h,
    ).json()
    ids = {item["id"] for item in listed}
    assert own_draft["id"] in ids
    assert colleague["id"] in ids

    got = api_client.get(f"/api/v1/consultations/{colleague['id']}", headers=a_h)
    assert got.status_code == 200
    assert got.json()["status"] == "finalized"
    assert api_client.patch(
        f"/api/v1/consultations/{colleague['id']}",
        headers=a_h,
        json={"reason": "Hack"},
    ).status_code == 403
    assert api_client.get(
        f"/api/v1/appointments/{data['appt_b'].id}/consultation",
        headers=a_h,
    ).status_code == 403

    owner_list = api_client.get(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=owner_h,
    ).json()
    assert len(owner_list) == 2


def test_professional_without_relationship_cannot_read_clinical_or_timeline(api_client, db_session):
    data = _seed_two_pros(db_session)
    stranger_patient = Patient(
        id=uuid4(), organization_id=data["org"].id,
        first_name="Lucía", last_name="Ajena", dni="40999888",
    )
    db_session.add(stranger_patient)
    db_session.commit()
    headers = _auth(api_client, data["prof_a"])
    assert api_client.get(
        f"/api/v1/patients/{stranger_patient.id}/consultations",
        headers=headers,
    ).status_code == 403
    assert api_client.get(
        f"/api/v1/patients/{stranger_patient.id}/clinical",
        headers=headers,
    ).status_code == 403


def test_professional_can_create_first_note_without_prior_relationship(api_client, db_session):
    data = _seed_two_pros(db_session)
    stranger_patient = Patient(
        id=uuid4(), organization_id=data["org"].id,
        first_name="Lucía", last_name="Ajena", dni="40999888",
    )
    db_session.add(stranger_patient)
    db_session.commit()
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.post(
        f"/api/v1/patients/{stranger_patient.id}/consultations",
        headers=headers,
        json={},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["appointment_id"] is None
    assert body["amends_id"] is None
    assert body["status"] == "draft"
    assert body["patient_id"] == str(stranger_patient.id)
    assert body["professional_id"] == str(data["prof_a"].id)

    listed = api_client.get(
        f"/api/v1/patients/{stranger_patient.id}/consultations",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]

    clinical = api_client.get(
        f"/api/v1/patients/{stranger_patient.id}/clinical",
        headers=headers,
    )
    assert clinical.status_code == 200


def test_professional_cannot_create_note_cross_org(api_client, db_session):
    data = _seed_two_pros(db_session)
    org2 = Organization(id=uuid4(), name="Otra 3", slug="otra-consultas-3")
    user2 = User(
        id=uuid4(), organization_id=org2.id, email="otro3@consultas.example.com",
        full_name="Otro 3", password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    db_session.add_all([org2, user2])
    db_session.commit()
    other = _auth(api_client, user2)
    resp = api_client.post(
        f"/api/v1/patients/{data['patient'].id}/consultations",
        headers=other,
        json={},
    )
    assert resp.status_code == 404


def test_owner_can_create_first_note_without_prior_relationship(api_client, db_session):
    data = _seed_two_pros(db_session)
    stranger_patient = Patient(
        id=uuid4(), organization_id=data["org"].id,
        first_name="Nora", last_name="Nueva", dni="40999777",
    )
    db_session.add(stranger_patient)
    db_session.commit()
    headers = _auth(api_client, data["owner"], data["password"])
    resp = api_client.post(
        f"/api/v1/patients/{stranger_patient.id}/consultations",
        headers=headers,
        json={},
    )
    assert resp.status_code == 201
    assert resp.json()["appointment_id"] is None
    assert resp.json()["amends_id"] is None
    assert resp.json()["professional_id"] == str(data["owner"].id)


