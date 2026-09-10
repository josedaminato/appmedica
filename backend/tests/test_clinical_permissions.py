"""Permisos de datos clínicos: staff sin campos clínicos, scope de professional."""

from datetime import datetime, timedelta, timezone
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
from app.models.user import User
from app.schemas.patient import CLINICAL_PATIENT_FIELDS

CLINICAL_ENDPOINTS = (
    "medical_history",
    "allergies",
    "current_medications",
    "clinical_notes",
)


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


def _seed(db_session: Session) -> dict:
    now = datetime.now(timezone.utc)
    org = Organization(id=uuid4(), name="Perm Org", slug="perm-org")
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email="owner@perm.example.com",
        full_name="Owner",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.OWNER,
    )
    prof_a = User(
        id=uuid4(),
        organization_id=org.id,
        email="profa@perm.example.com",
        full_name="Prof A",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    prof_b = User(
        id=uuid4(),
        organization_id=org.id,
        email="profb@perm.example.com",
        full_name="Prof B",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    staff = User(
        id=uuid4(),
        organization_id=org.id,
        email="staff@perm.example.com",
        full_name="Staff",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.STAFF,
    )
    patient_related = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Juan",
        last_name="Relacionado",
        dni="30111222",
        medical_history="HTA",
        allergies="Penicilina",
        current_medications="Losartán",
        clinical_notes="Control anual",
    )
    patient_unrelated = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="María",
        last_name="Ajena",
        dni="30222333",
        medical_history="Asma",
        allergies="Polen",
    )
    appt_a = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient_related.id,
        professional_id=prof_a.id,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    appt_b_only = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient_unrelated.id,
        professional_id=prof_b.id,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db_session.add_all([
        org, owner, prof_a, prof_b, staff,
        patient_related, patient_unrelated, appt_a, appt_b_only,
    ])
    db_session.commit()
    return {
        "org": org,
        "owner": owner,
        "prof_a": prof_a,
        "prof_b": prof_b,
        "staff": staff,
        "patient_related": patient_related,
        "patient_unrelated": patient_unrelated,
        "appt_a": appt_a,
        "appt_b_only": appt_b_only,
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
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _assert_no_clinical_fields(payload: dict) -> None:
    for field in CLINICAL_PATIENT_FIELDS:
        assert field not in payload, f"Campo clínico expuesto: {field}"


def test_staff_get_patient_excludes_clinical_fields(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["staff"])

    resp = api_client.get(f"/api/v1/patients/{data['patient_related'].id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Juan"
    _assert_no_clinical_fields(body)


def test_staff_list_patients_excludes_clinical_fields(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["staff"])

    resp = api_client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    for item in items:
        _assert_no_clinical_fields(item)


def test_staff_blocked_from_clinical_endpoints(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["staff"])
    pid = data["patient_related"].id

    assert api_client.get(f"/api/v1/patients/{pid}/clinical", headers=headers).status_code == 403
    assert api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"allergies": "X"},
    ).status_code == 403
    assert api_client.get(f"/api/v1/patients/{pid}/consultations", headers=headers).status_code == 403


def test_professional_clinical_via_appointment(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient_related"].id

    resp = api_client.get(f"/api/v1/patients/{pid}/clinical", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["medical_history"] == "HTA"


def test_professional_can_patch_clinical_related_patient(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient_related"].id

    resp = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"clinical_notes": "Seguimiento mensual"},
    )
    assert resp.status_code == 200
    assert resp.json()["clinical_notes"] == "Seguimiento mensual"


def test_professional_clinical_via_consultation_without_own_appointment(api_client, db_session):
    """Professional accede por Consultation aunque el turno sea de otro colega."""
    data = _seed(db_session)
    consultation = Consultation(
        id=uuid4(),
        organization_id=data["org"].id,
        appointment_id=data["appt_b_only"].id,
        patient_id=data["patient_unrelated"].id,
        professional_id=data["prof_a"].id,
        status=ConsultationStatus.DRAFT,
        created_by=data["prof_a"].id,
    )
    db_session.add(consultation)
    db_session.commit()

    headers = _auth(api_client, data["prof_a"])
    resp = api_client.get(
        f"/api/v1/patients/{data['patient_unrelated'].id}/clinical",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["medical_history"] == "Asma"


def test_professional_cannot_read_unrelated_patient_clinical(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient_unrelated"].id

    resp = api_client.get(f"/api/v1/patients/{pid}/clinical", headers=headers)
    assert resp.status_code == 403


def test_professional_cannot_patch_unrelated_patient_clinical(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])
    pid = data["patient_unrelated"].id

    resp = api_client.patch(
        f"/api/v1/patients/{pid}/clinical",
        headers=headers,
        json={"allergies": "Hack"},
    )
    assert resp.status_code == 403


def test_professional_cannot_access_clinical_cross_org(api_client, db_session):
    data = _seed(db_session)
    org2 = Organization(id=uuid4(), name="Otra", slug="otra-perm")
    user2 = User(
        id=uuid4(),
        organization_id=org2.id,
        email="profc@perm.example.com",
        full_name="Prof C",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.PROFESSIONAL,
    )
    db_session.add_all([org2, user2])
    db_session.commit()

    headers = _auth(api_client, user2)
    resp = api_client.get(
        f"/api/v1/patients/{data['patient_related'].id}/clinical",
        headers=headers,
    )
    assert resp.status_code == 404


def test_owner_can_read_and_patch_any_patient_clinical(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["owner"])

    for pid in (data["patient_related"].id, data["patient_unrelated"].id):
        get_resp = api_client.get(f"/api/v1/patients/{pid}/clinical", headers=headers)
        assert get_resp.status_code == 200

    patch = api_client.patch(
        f"/api/v1/patients/{data['patient_unrelated'].id}/clinical",
        headers=headers,
        json={"allergies": "Actualizado por owner"},
    )
    assert patch.status_code == 200
    assert patch.json()["allergies"] == "Actualizado por owner"


def test_professional_get_unrelated_patient_excludes_clinical_fields(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.get(f"/api/v1/patients/{data['patient_unrelated'].id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "María"
    assert body["last_name"] == "Ajena"
    _assert_no_clinical_fields(body)
    assert "Asma" not in resp.text
    assert "Polen" not in resp.text


def test_professional_list_excludes_clinical_for_unrelated_patients(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    by_id = {item["id"]: item for item in items}

    unrelated = by_id[str(data["patient_unrelated"].id)]
    assert unrelated["first_name"] == "María"
    _assert_no_clinical_fields(unrelated)
    assert unrelated.get("medical_history") != "Asma"
    assert "Asma" not in str(unrelated)
    assert "Polen" not in str(unrelated)

    related = by_id[str(data["patient_related"].id)]
    assert related["medical_history"] == "HTA"
    assert related["allergies"] == "Penicilina"


def test_professional_get_related_patient_includes_clinical_fields(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.get(f"/api/v1/patients/{data['patient_related'].id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["medical_history"] == "HTA"
    assert body["allergies"] == "Penicilina"
    assert body["current_medications"] == "Losartán"
    assert body["clinical_notes"] == "Control anual"


def test_owner_get_patient_includes_clinical_org_wide(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["owner"])

    related = api_client.get(f"/api/v1/patients/{data['patient_related'].id}", headers=headers)
    assert related.status_code == 200
    assert related.json()["medical_history"] == "HTA"

    unrelated = api_client.get(f"/api/v1/patients/{data['patient_unrelated'].id}", headers=headers)
    assert unrelated.status_code == 200
    assert unrelated.json()["medical_history"] == "Asma"
    assert unrelated.json()["allergies"] == "Polen"


def test_staff_get_patient_still_excludes_clinical_fields(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["staff"])

    resp = api_client.get(f"/api/v1/patients/{data['patient_related'].id}", headers=headers)
    assert resp.status_code == 200
    _assert_no_clinical_fields(resp.json())


def test_professional_list_cannot_leak_unrelated_clinical_values(api_client, db_session):
    data = _seed(db_session)
    headers = _auth(api_client, data["prof_a"])

    resp = api_client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    leaked_values = {"Asma", "Polen"}
    for item in payload["data"]:
        if item["id"] == str(data["patient_unrelated"].id):
            _assert_no_clinical_fields(item)
            for field in CLINICAL_PATIENT_FIELDS:
                assert item.get(field) not in leaked_values
            item_text = str(item)
            assert "Asma" not in item_text
            assert "Polen" not in item_text
