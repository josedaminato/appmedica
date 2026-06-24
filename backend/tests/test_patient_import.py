import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.enums import UserRole
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient_import import PatientImportCommitRequest
from app.services.column_alias import detect_column_mapping, normalize_column_name
from app.services.patient_import_service import PatientImportService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            User.__table__,
            Patient.__table__,
            HealthInsurance.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_org(session):
    org = Organization(name="Import Test", slug="import-test")
    session.add(org)
    session.flush()
    session.add(
        User(
            organization_id=org.id,
            email="t@t.com",
            full_name="T",
            role=UserRole.OWNER,
            password_hash="x",
        )
    )
    session.commit()
    return org


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Paciente", "paciente"),
        ("Nombre y Apellido", "nombre y apellido"),
        ("F. Nacimiento", "f nacimiento"),
        ("Teléfono", "telefono"),
        ("Nº_afiliado", "n afiliado"),
    ],
)
def test_normalize_column_name(raw, expected):
    assert normalize_column_name(raw) == expected


def test_detect_column_mapping_consultorio_typical():
    columns = [
        "Paciente",
        "Documento",
        "Celular",
        "Correo electrónico",
        "Prepaga",
        "F. Nacimiento",
    ]
    mapping = detect_column_mapping(columns)
    assert mapping["full_name"] == "Paciente"
    assert mapping["dni"] == "Documento"
    assert mapping["phone"] == "Celular"
    assert mapping["email"] == "Correo electrónico"
    assert mapping["health_insurance_name"] == "Prepaga"
    assert mapping["birth_date"] == "F. Nacimiento"


def test_preview_without_dni_is_valid(db_session):
    org = _seed_org(db_session)
    svc = PatientImportService(db_session)
    columns = ["Paciente", "Celular"]
    rows = [{"Paciente": "María García", "Celular": "2614112233"}]
    preview = svc.preview_from_rows(org.id, columns, rows, None)
    assert preview.summary["valid"] == 1
    assert preview.rows[0].status == "valid"
    assert preview.rows[0].data.dni is None


def test_preview_missing_name_is_error(db_session):
    org = _seed_org(db_session)
    svc = PatientImportService(db_session)
    preview = svc.preview_from_rows(
        org.id,
        ["Documento"],
        [{"Documento": "30123456"}],
        None,
    )
    assert preview.summary["error"] == 1
    assert "Falta nombre" in preview.rows[0].errors[0]


def test_commit_without_dni(db_session):
    org = _seed_org(db_session)
    svc = PatientImportService(db_session)
    preview = svc.preview_from_rows(
        org.id,
        ["Nombre y Apellido"],
        [{"Nombre y Apellido": "Juan Pérez"}],
        None,
    )
    valid = [r.data for r in preview.rows if r.status == "valid" and r.data]
    result = svc.commit(org.id, PatientImportCommitRequest(rows=valid))
    assert result.created == 1
    patient = db_session.query(Patient).one()
    assert patient.first_name == "Juan"
    assert patient.last_name == "Pérez"
    assert patient.dni is None


def test_in_file_duplicate_dni_marked(db_session):
    org = _seed_org(db_session)
    svc = PatientImportService(db_session)
    preview = svc.preview_from_rows(
        org.id,
        ["Nombre", "Apellido", "DNI"],
        [
            {"Nombre": "A", "Apellido": "Uno", "DNI": "30123456"},
            {"Nombre": "B", "Apellido": "Dos", "DNI": "30123456"},
        ],
        None,
    )
    assert preview.summary["valid"] == 1
    assert preview.summary["duplicate"] == 1
    assert preview.summary["to_import"] == 1
    assert preview.summary["omitted"] == 1
