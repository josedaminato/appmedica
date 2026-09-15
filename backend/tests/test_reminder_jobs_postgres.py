"""Garantías de reminder_jobs sobre PostgreSQL (unique parcial, SKIP LOCKED)."""

from __future__ import annotations

import asyncio
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, event, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.timezone import clamp_to_send_window
from app.integrations.reminders.base import ReminderPayload, ReminderSendResult
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
    ReminderChannel,
    ReminderKind,
    ReminderStatus,
    UserRole,
)
from app.models.health_insurance import HealthInsurance
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.reminder import ReminderJob
from app.models.user import User
from app.repositories.reminder_repository import ReminderRepository
from app.services.reminder_service import ReminderService

SCHEMA = "appmedica_reminder_test"
_SEND_WINDOW_LOCAL = datetime(2026, 6, 10, 10, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))


class _FrozenDateTime(datetime):
    """Subclass de datetime: datetime.now no se puede parchear (tipo C inmutable)."""

    @classmethod
    def now(cls, tz=None):
        frozen_utc = _SEND_WINDOW_LOCAL.astimezone(timezone.utc)
        if tz is None:
            return frozen_utc.replace(tzinfo=None)
        return frozen_utc.astimezone(tz)


@contextmanager
def _frozen_send_window():
    """Congela el reloj en la ventana de envío [08:00, 21:00] del consultorio."""
    with (
        patch(f"{__name__}.datetime", _FrozenDateTime),
        patch("app.services.reminder_service.datetime", _FrozenDateTime),
    ):
        yield _SEND_WINDOW_LOCAL.astimezone(timezone.utc)


def _in_send_window(fn):
    """Ejecuta el test con now determinístico; no mockea is_in_quiet_hours."""

    @wraps(fn)
    def sync_wrapper(*args, **kwargs):
        with _frozen_send_window():
            return fn(*args, **kwargs)

    @wraps(fn)
    async def async_wrapper(*args, **kwargs):
        with _frozen_send_window():
            return await fn(*args, **kwargs)

    if asyncio.iscoroutinefunction(fn):
        return async_wrapper
    return sync_wrapper


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
        pytest.skip(f"PostgreSQL no disponible para tests de reminder_jobs: {exc}")

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
        ReminderJob.__table__,
    ):
        table.create(engine, checkfirst=True)
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


def _settings(**overrides) -> Settings:
    data = {
        "reminders_enabled": True,
        "reminder_hours_before": 24,
        "email_provider": "smtp",
        "smtp_host": "localhost",
        "smtp_user": "user",
        "smtp_password": "pass",
        "whatsapp_provider": "disabled",
        "app_env": "development",
    }
    data.update(overrides)
    return Settings(**data)


class ScriptedProvider:
    def __init__(self, results: list[ReminderSendResult] | None = None) -> None:
        self.results = list(results or [])
        self.payloads: list[ReminderPayload] = []

    async def send(self, payload: ReminderPayload) -> ReminderSendResult:
        self.payloads.append(payload)
        if self.results:
            return self.results.pop(0)
        return ReminderSendResult.success()


def _seed(db: Session, *, email: str = "ana@clinic.test", phone: str | None = "2615550000"):
    now = datetime.now(timezone.utc)
    org = Organization(id=uuid4(), name="Clinic", slug=f"clinic-{uuid4().hex[:8]}")
    owner = User(
        id=uuid4(),
        organization_id=org.id,
        email=f"owner-{uuid4().hex[:8]}@clinic.test",
        full_name="Owner",
        password_hash="x",
        role=UserRole.OWNER,
    )
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Ana",
        last_name="Pérez",
        dni=str(uuid4().int)[:8],
        email=email,
        phone=phone,
    )
    appt = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=owner.id,
        start_at=now + timedelta(hours=48),
        end_at=now + timedelta(hours=49),
        status=AppointmentStatus.PENDING,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db.add_all([org, owner, patient, appt])
    db.commit()
    return org, owner, patient, appt


def _job(db: Session, org, patient, appt, **overrides) -> ReminderJob:
    now = datetime.now(timezone.utc)
    job = ReminderJob(
        organization_id=org.id,
        appointment_id=appt.id,
        patient_id=patient.id,
        kind=ReminderKind.APPOINTMENT_REMINDER_24H,
        channel=ReminderChannel.EMAIL,
        status=ReminderStatus.SCHEDULED,
        scheduled_at=now - timedelta(minutes=1),
        next_attempt_at=now - timedelta(minutes=1),
        attempt_count=0,
        **overrides,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def _process(db: Session, settings: Settings, provider: ScriptedProvider, org_id=None):
    service = ReminderService(db, settings)
    return await service.process_due_jobs(
        organization_id=org_id,
        email_provider=provider,
        whatsapp_provider=provider,
    )


def test_schedule_creates_single_job(db: Session):
    org, _owner, patient, appt = _seed(db)
    service = ReminderService(db, _settings())
    jobs = service.schedule_for_appointment(org.id, appt.id)
    assert len(jobs) == 1
    assert jobs[0].appointment_id == appt.id
    assert jobs[0].channel == ReminderChannel.EMAIL
    assert jobs[0].status == ReminderStatus.SCHEDULED
    rows = db.query(ReminderJob).filter(ReminderJob.appointment_id == appt.id).all()
    assert len(rows) == 1
    assert patient.email == "ana@clinic.test"


def test_schedule_twice_keeps_one_active(db: Session):
    org, _owner, _patient, appt = _seed(db)
    service = ReminderService(db, _settings())
    first = service.schedule_for_appointment(org.id, appt.id)
    second = service.schedule_for_appointment(org.id, appt.id)
    assert len(first) == 1
    assert len(second) == 1
    active = (
        db.query(ReminderJob)
        .filter(
            ReminderJob.appointment_id == appt.id,
            ReminderJob.status.in_(
                [ReminderStatus.SCHEDULED, ReminderStatus.SENDING, ReminderStatus.SENT],
            ),
        )
        .all()
    )
    assert len(active) == 1


def test_postgres_rejects_duplicate_active_jobs(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    db.add(
        ReminderJob(
            organization_id=org.id,
            appointment_id=appt.id,
            patient_id=patient.id,
            kind=ReminderKind.APPOINTMENT_REMINDER_24H,
            channel=ReminderChannel.EMAIL,
            status=ReminderStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc),
            next_attempt_at=datetime.now(timezone.utc),
            attempt_count=0,
        ),
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_skip_locked_second_session_sees_nothing(db: Session, pg_engine):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    session_a = SessionLocal()
    session_b = SessionLocal()
    try:
        now = datetime.now(timezone.utc) + timedelta(minutes=1)
        locked = ReminderRepository(session_a).lock_due_job(before=now)
        assert locked is not None
        skipped = ReminderRepository(session_b).lock_due_job(before=now)
        assert skipped is None
    finally:
        session_a.rollback()
        session_b.rollback()
        session_a.close()
        session_b.close()


@_in_send_window
def test_two_processors_send_once(db: Session, pg_engine):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    settings = _settings()
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    results: list[dict | None] = [None, None]

    def worker(index: int) -> None:
        session = SessionLocal()
        try:
            results[index] = asyncio.run(
                ReminderService(session, settings).process_due_jobs(
                    email_provider=ScriptedProvider(),
                    whatsapp_provider=ScriptedProvider(),
                ),
            )
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(0,)), threading.Thread(target=worker, args=(1,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results[0] is not None and results[1] is not None
    assert results[0]["sent"] + results[1]["sent"] == 1
    assert results[0]["processed"] + results[1]["processed"] == 1
    db.expire_all()
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.SENT


async def test_cancelled_appointment_does_not_send(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    appt.status = AppointmentStatus.CANCELLED
    db.commit()
    provider = ScriptedProvider()
    result = await _process(db, _settings(), provider)
    assert result["processed"] == 1
    assert provider.payloads == []
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.CANCELLED
    assert job.error_code == "appointment_cancelled"


async def test_reschedule_cancels_old_and_schedules_new(db: Session):
    org, owner, patient, old = _seed(db)
    service = ReminderService(db, _settings())
    created = service.schedule_for_appointment(org.id, old.id)
    assert created
    now = datetime.now(timezone.utc)
    new = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=owner.id,
        start_at=now + timedelta(hours=72),
        end_at=now + timedelta(hours=73),
        status=AppointmentStatus.PENDING,
        modality=AppointmentModality.IN_PERSON,
        attention_type=AttentionType.PRIVATE,
        closure_status=AppointmentClosureStatus.NONE,
    )
    db.add(new)
    db.flush()
    old.status = AppointmentStatus.RESCHEDULED
    old.rescheduled_to_id = new.id
    db.commit()
    service.cancel_for_appointment(org.id, old.id)
    service.schedule_for_appointment(org.id, new.id)
    old_jobs = db.query(ReminderJob).filter(ReminderJob.appointment_id == old.id).all()
    new_jobs = db.query(ReminderJob).filter(ReminderJob.appointment_id == new.id).all()
    assert all(j.status == ReminderStatus.CANCELLED for j in old_jobs)
    assert len(new_jobs) == 1
    assert new_jobs[0].status == ReminderStatus.SCHEDULED


async def test_past_appointment_is_skipped(db: Session):
    org, _owner, patient, appt = _seed(db)
    appt.start_at = datetime.now(timezone.utc) - timedelta(hours=1)
    appt.end_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.commit()
    _job(db, org, patient, appt)
    provider = ScriptedProvider()
    await _process(db, _settings(), provider)
    assert provider.payloads == []
    assert db.query(ReminderJob).one().status == ReminderStatus.SKIPPED
    assert db.query(ReminderJob).one().error_code == "appointment_past"


@_in_send_window
async def test_uses_current_patient_phone(db: Session):
    org, _owner, patient, appt = _seed(db, phone="111111")
    settings = _settings(whatsapp_provider="twilio", email_provider="mock")
    service = ReminderService(db, settings)
    jobs = service.schedule_for_appointment(org.id, appt.id)
    assert len(jobs) == 1
    assert jobs[0].channel == ReminderChannel.WHATSAPP
    jobs[0].next_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    patient.phone = "222222"
    db.commit()
    provider = ScriptedProvider()
    await ReminderService(db, settings).process_due_jobs(
        email_provider=ScriptedProvider(),
        whatsapp_provider=provider,
    )
    assert provider.payloads[0].phone == "222222"


@_in_send_window
async def test_5xx_schedules_retry(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider([
        ReminderSendResult.failure(retryable=True, http_status=503, error_code="http_503"),
    ])
    result = await _process(db, _settings(), provider)
    assert result["retried"] == 1
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.SCHEDULED
    assert job.attempt_count == 1
    assert job.next_attempt_at > datetime.now(timezone.utc)
    assert job.error_code == "http_503"


@_in_send_window
async def test_429_uses_retry_after(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    before = datetime.now(timezone.utc)
    provider = ScriptedProvider([
        ReminderSendResult.failure(
            retryable=True,
            http_status=429,
            retry_after_seconds=90,
            error_code="http_429",
        ),
    ])
    await _process(db, _settings(), provider)
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.SCHEDULED
    assert job.error_code == "http_429"
    tz = ZoneInfo(org.timezone or "America/Argentina/Buenos_Aires")
    expected = clamp_to_send_window(before + timedelta(seconds=90), tz)
    assert abs((job.next_attempt_at - expected).total_seconds()) < 15


@_in_send_window
async def test_4xx_is_terminal_failed(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider([
        ReminderSendResult.failure(retryable=False, http_status=400, error_code="http_400"),
    ])
    result = await _process(db, _settings(), provider)
    assert result["failed"] == 1
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.FAILED
    assert job.error_code == "http_400"
    assert job.attempt_count == 1


@_in_send_window
async def test_orphan_sending_is_recovered(db: Session):
    org, _owner, patient, appt = _seed(db)
    job = _job(db, org, patient, appt)
    db.execute(
        update(ReminderJob)
        .where(ReminderJob.id == job.id)
        .values(
            status=ReminderStatus.SENDING,
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=11),
        ),
    )
    db.commit()
    provider = ScriptedProvider()
    result = await _process(db, _settings(), provider)
    assert result["sent"] == 1
    db.refresh(job)
    assert job.status == ReminderStatus.SENT


async def test_missing_contact_skipped(db: Session):
    org, _owner, patient, appt = _seed(db, email="ana@clinic.test")
    _job(db, org, patient, appt)
    patient.email = None
    db.commit()
    provider = ScriptedProvider()
    await _process(db, _settings(), provider)
    assert provider.payloads == []
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "missing_contact"


@_in_send_window
async def test_retry_after_start_is_skipped(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider([
        ReminderSendResult.failure(
            retryable=True,
            http_status=429,
            retry_after_seconds=int(timedelta(hours=50).total_seconds()),
            error_code="http_429",
        ),
    ])
    result = await _process(db, _settings(), provider)
    assert result["skipped"] == 1
    job = db.query(ReminderJob).one()
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "retry_after_start"


async def test_organization_isolation(db: Session):
    org_a, _owner_a, patient_a, appt_a = _seed(db)
    org_b, _owner_b, patient_b, appt_b = _seed(db)
    _job(db, org_b, patient_b, appt_b)
    provider = ScriptedProvider()
    result = await _process(db, _settings(), provider, org_id=org_a.id)
    assert result["processed"] == 0
    assert db.query(ReminderJob).filter(ReminderJob.appointment_id == appt_b.id).one().status == (
        ReminderStatus.SCHEDULED
    )
    mismatched = ReminderJob(
        organization_id=org_a.id,
        appointment_id=appt_b.id,
        patient_id=patient_a.id,
        kind=ReminderKind.APPOINTMENT_REMINDER_24H,
        channel=ReminderChannel.WHATSAPP,
        status=ReminderStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        attempt_count=0,
    )
    db.add(mismatched)
    db.commit()
    await _process(db, _settings(whatsapp_provider="twilio"), ScriptedProvider(), org_id=org_a.id)
    db.refresh(mismatched)
    assert mismatched.status == ReminderStatus.SKIPPED
    assert mismatched.error_code == "appointment_missing"


def test_lead_window_two_hours_still_schedules(db: Session):
    """Faltan 2 horas en ventana diurna: sí se crea job (no hay piso de 3h)."""
    org, _owner, _patient, appt = _seed(db)
    org.timezone = "America/Argentina/Buenos_Aires"
    now = datetime(2026, 6, 10, 16, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
    appt.start_at = now + timedelta(hours=2)
    appt.end_at = now + timedelta(hours=3)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(
        org.id, appt.id, now=now,
    )
    assert len(jobs) == 1
    assert jobs[0].status == ReminderStatus.SCHEDULED
    assert jobs[0].next_attempt_at == now.astimezone(timezone.utc)


def test_case3_ninety_minutes_creates_job(db: Session):
    org, _owner, _patient, appt = _seed(db)
    now = datetime(2026, 6, 10, 18, 30, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
    appt.start_at = datetime(2026, 6, 10, 20, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert len(jobs) == 1
    assert jobs[0].next_attempt_at == now.astimezone(timezone.utc)


def test_case4_morning_clamp_creates_job_for_0800(db: Session):
    org, _owner, _patient, appt = _seed(db)
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    now = datetime(2026, 6, 10, 6, 30, tzinfo=tz)
    appt.start_at = datetime(2026, 6, 10, 9, 0, tzinfo=tz)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert len(jobs) == 1
    assert jobs[0].next_attempt_at == datetime(2026, 6, 10, 8, 0, tzinfo=tz).astimezone(timezone.utc)


def test_case6_start_at_change_cancels_and_recalculates(db: Session):
    org, _owner, _patient, appt = _seed(db)
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    service = ReminderService(db, _settings())
    created = service.schedule_for_appointment(org.id, appt.id)
    assert created
    old_id = created[0].id
    now = datetime(2026, 6, 10, 8, 30, tzinfo=tz)
    appt.start_at = datetime(2026, 6, 10, 10, 0, tzinfo=tz)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = service.schedule_for_appointment(org.id, appt.id, now=now)
    assert len(jobs) == 1
    assert jobs[0].id != old_id
    old = db.query(ReminderJob).filter(ReminderJob.id == old_id).one()
    assert old.status == ReminderStatus.CANCELLED
    assert jobs[0].next_attempt_at == now.astimezone(timezone.utc)


def test_case7_exactly_30_minutes_after_update(db: Session):
    org, _owner, _patient, appt = _seed(db)
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id)
    now = datetime(2026, 6, 10, 9, 30, tzinfo=tz)
    appt.start_at = datetime(2026, 6, 10, 10, 0, tzinfo=tz)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert len(jobs) == 1


def test_case8_under_30_minutes_after_update_does_not_create(db: Session):
    org, _owner, _patient, appt = _seed(db)
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id)
    now = datetime(2026, 6, 10, 9, 31, tzinfo=tz)
    appt.start_at = datetime(2026, 6, 10, 10, 0, tzinfo=tz)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert jobs == []
    active = (
        db.query(ReminderJob)
        .filter(
            ReminderJob.appointment_id == appt.id,
            ReminderJob.status.in_(
                [ReminderStatus.SCHEDULED, ReminderStatus.SENDING, ReminderStatus.SENT],
            ),
        )
        .all()
    )
    assert active == []


def test_case9_overnight_0800_does_not_create(db: Session):
    org, _owner, _patient, appt = _seed(db)
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    now = datetime(2026, 6, 9, 23, 30, tzinfo=tz)
    appt.start_at = datetime(2026, 6, 10, 8, 0, tzinfo=tz)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert jobs == []
    assert db.query(ReminderJob).filter(ReminderJob.appointment_id == appt.id).count() == 0


def test_case10_started_appointment_does_not_schedule(db: Session):
    org, _owner, _patient, appt = _seed(db)
    now = datetime.now(timezone.utc)
    appt.start_at = now - timedelta(minutes=1)
    appt.end_at = now + timedelta(minutes=29)
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert jobs == []


def test_case11_cancelled_appointment_does_not_schedule(db: Session):
    org, _owner, _patient, appt = _seed(db)
    appt.status = AppointmentStatus.CANCELLED
    db.commit()
    jobs = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id)
    assert jobs == []


def test_sent_job_blocks_second_schedule_after_start_change(db: Session):
    org, _owner, patient, appt = _seed(db)
    job = _job(db, org, patient, appt)
    job.status = ReminderStatus.SENT
    db.commit()
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    now = datetime(2026, 6, 10, 16, 0, tzinfo=tz)
    appt.start_at = now + timedelta(hours=3)
    appt.end_at = appt.start_at + timedelta(minutes=30)
    db.commit()
    created = ReminderService(db, _settings()).schedule_for_appointment(org.id, appt.id, now=now)
    assert created == []
    db.refresh(job)
    assert job.status == ReminderStatus.SENT


@_in_send_window
async def test_valid_due_job_sends_normally(db: Session):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider()
    result = await _process(db, _settings(), provider)
    assert result["sent"] == 1
    assert len(provider.payloads) == 1
    stored = db.query(ReminderJob).one()
    assert stored.status == ReminderStatus.SENT


@_in_send_window
async def test_cancel_before_send_does_not_call_provider(db: Session, pg_engine):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider()
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    appointment_id = appt.id

    def cancel_appointment() -> None:
        session = SessionLocal()
        try:
            row = session.get(Appointment, appointment_id)
            assert row is not None
            row.status = AppointmentStatus.CANCELLED
            session.commit()
        finally:
            session.close()

    class HookedReminderService(ReminderService):
        def _revalidate_before_provider(self, prepared):
            cancel_appointment()
            return super()._revalidate_before_provider(prepared)

    result = await HookedReminderService(db, _settings()).process_due_jobs(
        email_provider=provider,
        whatsapp_provider=provider,
    )
    assert provider.payloads == []
    assert result["sent"] == 0
    db.expire_all()
    stored = db.query(ReminderJob).one()
    assert stored.status == ReminderStatus.CANCELLED
    assert stored.error_code == "appointment_cancelled"


@_in_send_window
async def test_start_at_change_before_send_does_not_send_old_reminder(db: Session, pg_engine):
    org, _owner, patient, appt = _seed(db)
    _job(db, org, patient, appt)
    provider = ScriptedProvider()
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    appointment_id = appt.id

    def change_start() -> None:
        session = SessionLocal()
        try:
            row = session.get(Appointment, appointment_id)
            assert row is not None
            row.start_at = row.start_at + timedelta(hours=24)
            row.end_at = row.end_at + timedelta(hours=24)
            session.commit()
        finally:
            session.close()

    class HookedReminderService(ReminderService):
        def _revalidate_before_provider(self, prepared):
            change_start()
            return super()._revalidate_before_provider(prepared)

    result = await HookedReminderService(db, _settings()).process_due_jobs(
        email_provider=provider,
        whatsapp_provider=provider,
    )
    assert provider.payloads == []
    assert result["sent"] == 0
    db.expire_all()
    stored = db.query(ReminderJob).one()
    assert stored.status == ReminderStatus.SKIPPED
    assert stored.error_code == "appointment_start_changed"


@_in_send_window
async def test_provider_success_does_not_overwrite_cancelled(db: Session, pg_engine):
    org, _owner, patient, appt = _seed(db)
    job = _job(db, org, patient, appt)
    SessionLocal = sessionmaker(bind=pg_engine, expire_on_commit=False)
    job_id = job.id

    class CancelDuringSend(ScriptedProvider):
        async def send(self, payload: ReminderPayload) -> ReminderSendResult:
            self.payloads.append(payload)
            session = SessionLocal()
            try:
                session.execute(
                    update(ReminderJob)
                    .where(ReminderJob.id == job_id)
                    .values(
                        status=ReminderStatus.CANCELLED,
                        error_code="appointment_cancelled",
                    ),
                )
                session.commit()
            finally:
                session.close()
            return ReminderSendResult.success()

    provider = CancelDuringSend()
    result = await _process(db, _settings(), provider)
    assert len(provider.payloads) == 1
    assert result["sent"] == 0
    db.expire_all()
    stored = db.query(ReminderJob).one()
    assert stored.status == ReminderStatus.CANCELLED
    assert stored.error_code == "appointment_cancelled"


def test_update_if_sending_does_not_overwrite_cancelled(db: Session):
    org, _owner, patient, appt = _seed(db)
    job = _job(db, org, patient, appt)
    job.status = ReminderStatus.SENDING
    db.commit()
    cancelled = ReminderRepository(db).cancel_scheduled_for_appointment(org.id, appt.id)
    db.commit()
    assert cancelled == 1
    applied = ReminderRepository(db).update_if_sending(
        job.id,
        {
            "status": ReminderStatus.SENT,
            "error_code": None,
            "error_message": None,
        },
    )
    db.commit()
    assert applied is False
    db.refresh(job)
    assert job.status == ReminderStatus.CANCELLED
    assert job.error_code == "appointment_cancelled"
