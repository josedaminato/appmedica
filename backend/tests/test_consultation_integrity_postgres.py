"""Integridad de consultations sobre PostgreSQL (FK RESTRICT + triggers)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, event, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.consultation_integrity import (
    CONSULTATION_BACKFILL_OCCURRED_AT_FROM_APPOINTMENT_SQL,
    CONSULTATION_BACKFILL_OCCURRED_AT_FROM_CREATED_AT_SQL,
    apply_consultation_amendment_chain_ddl,
    apply_consultation_immutability_ddl,
)
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
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User

SCHEMA = "appmedica_consultation_integrity_test"


def _postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    url = os.environ.get("DATABASE_URL", "")
    if "postgresql" in url:
        return url
    return "postgresql+psycopg://appmedica:appmedica_secret@127.0.0.1:5432/appmedica?sslmode=disable"


@pytest.fixture(scope="module")
def pg_engine():
    url = _postgres_url()
    if "postgresql" not in url:
        pytest.skip("TEST_DATABASE_URL / DATABASE_URL no apunta a PostgreSQL")
    raw = create_engine(url, pool_pre_ping=True)
    try:
        with raw.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
    except Exception as exc:
        pytest.skip(f"PostgreSQL no disponible para tests de integridad de consultations: {exc}")

    with raw.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {SCHEMA}"))

    @event.listens_for(raw, "connect")
    def _search_path(dbapi_conn, _record):
        with dbapi_conn.cursor() as cur:
            cur.execute(f"SET search_path TO {SCHEMA}")

    raw.dispose()
    engine = raw.execution_options(schema_translate_map={None: SCHEMA})
    for table in (
        Organization.__table__,
        User.__table__,
        HealthInsurance.__table__,
        Patient.__table__,
        Appointment.__table__,
        Consultation.__table__,
    ):
        table.create(engine, checkfirst=True)
    with engine.begin() as conn:
        apply_consultation_immutability_ddl(conn)
        apply_consultation_amendment_chain_ddl(conn)
    yield engine
    with raw.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
    raw.dispose()


@pytest.fixture()
def db(pg_engine) -> Session:
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.execute(text(f"TRUNCATE TABLE {SCHEMA}.organizations CASCADE"))
    session.commit()
    session.close()


def _seed(db: Session):
    now = datetime.now(timezone.utc)
    org = Organization(id=uuid4(), name="Clinic", slug=f"clinic-{uuid4().hex[:8]}")
    professional = User(
        id=uuid4(),
        organization_id=org.id,
        email=f"pro-{uuid4().hex[:8]}@clinic.test",
        full_name="Dr. Juan Pérez",
        license_number="MN 12345",
        password_hash="x",
        role=UserRole.PROFESSIONAL,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Pérez",
        dni=str(uuid4().int)[:8],
    )
    appointment = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=professional.id,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status=AppointmentStatus.ATTENDED,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db.add_all([org, professional, patient, appointment])
    db.commit()
    return org, professional, patient, appointment


def _draft_consultation(db: Session, org, professional, patient, appointment) -> Consultation:
    row = Consultation(
        organization_id=org.id,
        appointment_id=appointment.id,
        patient_id=patient.id,
        professional_id=professional.id,
        reason="Motivo",
        evolution="Evolución",
        status=ConsultationStatus.DRAFT,
        created_by=professional.id,
        updated_by=professional.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _finalize_via_orm(db: Session, row: Consultation, professional: User) -> Consultation:
    row.professional_name_snapshot = professional.full_name
    row.professional_license_snapshot = professional.license_number
    row.status = ConsultationStatus.FINALIZED
    db.commit()
    db.refresh(row)
    return row


def _is_db_rejection(exc: BaseException, fragment: str) -> bool:
    text_blob = str(exc).lower()
    orig = getattr(exc, "orig", None)
    if orig is not None:
        text_blob = f"{text_blob} {orig}".lower()
    return fragment.lower() in text_blob


def test_postgres_rejects_delete_of_appointment_with_consultation(db: Session):
    org, professional, patient, appointment = _seed(db)
    consultation = _draft_consultation(db, org, professional, patient, appointment)

    with pytest.raises(IntegrityError):
        db.execute(
            text("DELETE FROM appointments WHERE id = :id"),
            {"id": appointment.id},
        )
        db.commit()
    db.rollback()
    remaining = db.get(Appointment, appointment.id)
    assert remaining is not None
    assert remaining.id == appointment.id
    assert db.get(Consultation, consultation.id) is not None


def test_postgres_rejects_direct_update_of_finalized_consultation(db: Session):
    org, professional, patient, appointment = _seed(db)
    row = _finalize_via_orm(
        db,
        _draft_consultation(db, org, professional, patient, appointment),
        professional,
    )

    with pytest.raises(DBAPIError) as exc:
        db.execute(
            update(Consultation).where(Consultation.id == row.id).values(reason="hack"),
        )
        db.commit()
    db.rollback()
    assert _is_db_rejection(exc.value, "cannot be modified")

    stored = db.get(Consultation, row.id)
    assert stored.reason == "Motivo"
    assert stored.status == ConsultationStatus.FINALIZED


def test_postgres_rejects_direct_delete_of_finalized_consultation(db: Session):
    org, professional, patient, appointment = _seed(db)
    row = _finalize_via_orm(
        db,
        _draft_consultation(db, org, professional, patient, appointment),
        professional,
    )

    with pytest.raises(DBAPIError) as exc:
        db.execute(delete(Consultation).where(Consultation.id == row.id))
        db.commit()
    db.rollback()
    assert _is_db_rejection(exc.value, "cannot be deleted")
    assert db.get(Consultation, row.id) is not None


def test_postgres_allows_update_of_draft_consultation(db: Session):
    org, professional, patient, appointment = _seed(db)
    row = _draft_consultation(db, org, professional, patient, appointment)

    db.execute(
        update(Consultation).where(Consultation.id == row.id).values(diagnosis="Lumbalgia"),
    )
    db.commit()
    stored = db.get(Consultation, row.id)
    assert stored.diagnosis == "Lumbalgia"
    assert stored.status == ConsultationStatus.DRAFT


def test_postgres_allows_draft_to_finalized_transition(db: Session):
    org, professional, patient, appointment = _seed(db)
    row = _draft_consultation(db, org, professional, patient, appointment)

    db.execute(
        update(Consultation)
        .where(Consultation.id == row.id)
        .values(
            status=ConsultationStatus.FINALIZED,
            professional_name_snapshot=professional.full_name,
            professional_license_snapshot=professional.license_number,
        ),
    )
    db.commit()
    stored = db.get(Consultation, row.id)
    assert stored.status == ConsultationStatus.FINALIZED
    assert stored.professional_name_snapshot == "Dr. Juan Pérez"


def _amendment(db: Session, original: Consultation, *, reason: str = "Corrección") -> Consultation:
    row = Consultation(
        organization_id=original.organization_id,
        appointment_id=original.appointment_id,
        patient_id=original.patient_id,
        professional_id=original.professional_id,
        amends_id=original.id,
        amend_reason=reason,
        occurred_at=original.occurred_at,
        status=ConsultationStatus.DRAFT,
        created_by=original.created_by,
        updated_by=original.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_postgres_partial_unique_rejects_second_primary_for_appointment(db: Session):
    org, professional, patient, appointment = _seed(db)
    _draft_consultation(db, org, professional, patient, appointment)

    with pytest.raises(IntegrityError):
        _draft_consultation(db, org, professional, patient, appointment)
    db.rollback()


def test_postgres_allows_amendment_with_same_appointment_id(db: Session):
    org, professional, patient, appointment = _seed(db)
    original = _draft_consultation(db, org, professional, patient, appointment)
    amendment = _amendment(db, original)

    assert amendment.appointment_id == appointment.id
    assert amendment.amends_id == original.id
    rows = db.execute(
        text(
            """
            SELECT COUNT(*) FROM consultations
            WHERE appointment_id = :appointment_id AND amends_id IS NULL
            """
        ),
        {"appointment_id": appointment.id},
    ).scalar()
    assert rows == 1
    total = db.execute(
        text("SELECT COUNT(*) FROM consultations WHERE appointment_id = :appointment_id"),
        {"appointment_id": appointment.id},
    ).scalar()
    assert total == 2


def test_postgres_allows_consultation_without_appointment(db: Session):
    org, professional, patient, _appointment = _seed(db)
    occurred = datetime(2026, 3, 1, 15, 30, tzinfo=timezone.utc)
    row = Consultation(
        organization_id=org.id,
        appointment_id=None,
        patient_id=patient.id,
        professional_id=professional.id,
        occurred_at=occurred,
        status=ConsultationStatus.DRAFT,
        created_by=professional.id,
        updated_by=professional.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    assert row.appointment_id is None
    assert row.amends_id is None
    assert row.occurred_at == occurred


def test_postgres_allows_occurred_at_older_than_thirty_days(db: Session):
    org, professional, patient, _appointment = _seed(db)
    occurred = datetime.now(timezone.utc) - timedelta(days=90)
    row = Consultation(
        organization_id=org.id,
        appointment_id=None,
        patient_id=patient.id,
        professional_id=professional.id,
        occurred_at=occurred,
        status=ConsultationStatus.DRAFT,
        created_by=professional.id,
        updated_by=professional.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    assert row.occurred_at == occurred


def test_postgres_rejects_amendment_without_reason(db: Session):
    org, professional, patient, appointment = _seed(db)
    original = _draft_consultation(db, org, professional, patient, appointment)
    db.add(
        Consultation(
            organization_id=org.id,
            appointment_id=appointment.id,
            patient_id=patient.id,
            professional_id=professional.id,
            amends_id=original.id,
            amend_reason=None,
            status=ConsultationStatus.DRAFT,
            created_by=professional.id,
        ),
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_postgres_rejects_blank_amend_reason(db: Session):
    org, professional, patient, appointment = _seed(db)
    original = _draft_consultation(db, org, professional, patient, appointment)
    db.add(
        Consultation(
            organization_id=org.id,
            appointment_id=appointment.id,
            patient_id=patient.id,
            professional_id=professional.id,
            amends_id=original.id,
            amend_reason="   ",
            status=ConsultationStatus.DRAFT,
            created_by=professional.id,
        ),
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_postgres_rejects_amendment_chain(db: Session):
    org, professional, patient, appointment = _seed(db)
    original = _draft_consultation(db, org, professional, patient, appointment)
    first_fix = _amendment(db, original)

    db.add(
        Consultation(
            organization_id=org.id,
            appointment_id=appointment.id,
            patient_id=patient.id,
            professional_id=professional.id,
            amends_id=first_fix.id,
            amend_reason="Segunda corrección encadenada",
            status=ConsultationStatus.DRAFT,
            created_by=professional.id,
        ),
    )
    with pytest.raises(DBAPIError) as exc:
        db.commit()
    db.rollback()
    assert _is_db_rejection(exc.value, "amends_id must reference an original")


def test_postgres_backfills_occurred_at_from_appointment_then_created_at(db: Session):
    org, professional, patient, appointment = _seed(db)
    linked = _draft_consultation(db, org, professional, patient, appointment)
    assert linked.occurred_at is None
    note = Consultation(
        organization_id=org.id,
        appointment_id=None,
        patient_id=patient.id,
        professional_id=professional.id,
        occurred_at=None,
        status=ConsultationStatus.DRAFT,
        created_by=professional.id,
        updated_by=professional.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    note_created_at = note.created_at
    assert note.occurred_at is None

    db.execute(text(CONSULTATION_BACKFILL_OCCURRED_AT_FROM_APPOINTMENT_SQL))
    db.execute(text(CONSULTATION_BACKFILL_OCCURRED_AT_FROM_CREATED_AT_SQL))
    db.commit()
    db.refresh(linked)
    db.refresh(note)

    assert linked.occurred_at == appointment.start_at
    assert note.occurred_at == note_created_at


def test_postgres_backfill_does_not_overwrite_existing_occurred_at(db: Session):
    org, professional, patient, appointment = _seed(db)
    custom = datetime(2025, 6, 1, 8, 0, tzinfo=timezone.utc)
    row = Consultation(
        organization_id=org.id,
        appointment_id=appointment.id,
        patient_id=patient.id,
        professional_id=professional.id,
        occurred_at=custom,
        status=ConsultationStatus.DRAFT,
        created_by=professional.id,
        updated_by=professional.id,
    )
    db.add(row)
    db.commit()
    db.execute(text(CONSULTATION_BACKFILL_OCCURRED_AT_FROM_APPOINTMENT_SQL))
    db.execute(text(CONSULTATION_BACKFILL_OCCURRED_AT_FROM_CREATED_AT_SQL))
    db.commit()
    db.refresh(row)
    assert row.occurred_at == custom
