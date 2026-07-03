from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.billing import add_calendar_month, extend_paid_period, payment_status
from app.core.config import get_settings
from app.services.platform_service import PlatformService
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.appointment import Appointment
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    for table in (
        Organization.__table__,
        User.__table__,
        Patient.__table__,
        Appointment.__table__,
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


@pytest.fixture()
def platform_client(db_session: Session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PLATFORM_ADMIN_USERNAME", "daminato88")
    monkeypatch.setenv("PLATFORM_ADMIN_PASSWORD", "Riverplate1988")
    get_settings.cache_clear()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_billing_month_rollover():
    assert add_calendar_month(date(2026, 1, 31)) == date(2026, 2, 28)
    assert add_calendar_month(date(2026, 3, 15)) == date(2026, 4, 15)


def test_payment_status_overdue():
    status, days = payment_status(date(2026, 1, 1))
    assert status == "overdue"
    assert days is not None and days < 0


def test_extend_paid_period_from_today(monkeypatch):
    class FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 1)

    monkeypatch.setattr(
        "app.core.billing.datetime",
        type("DT", (), {"now": staticmethod(lambda tz=None: datetime(2026, 6, 1, tzinfo=timezone.utc))}),
    )
    monkeypatch.setattr("app.core.billing.date", FakeDate)
    assert extend_paid_period(None) == date(2026, 7, 1)


def test_platform_login_and_dashboard(platform_client: TestClient, db_session: Session):
    org = Organization(
        id=uuid4(),
        name="Consultorio Test",
        slug="consultorio-test",
        service_started_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        paid_until=date(2026, 5, 1),
        monthly_fee=Decimal("25000"),
    )
    db_session.add(org)
    db_session.add(
        User(
            organization_id=org.id,
            email="owner@test.com",
            password_hash=hash_password("testpass123"),
            full_name="Dueño Test",
            role=UserRole.OWNER,
            is_active=True,
        )
    )
    db_session.commit()

    bad = platform_client.post("/api/v1/platform/login", json={"username": "xx", "password": "wrongpass1"})
    assert bad.status_code == 401

    login = platform_client.post(
        "/api/v1/platform/login",
        json={"username": "daminato88", "password": "Riverplate1988"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    dash = platform_client.get("/api/v1/platform/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash.status_code == 200
    body = dash.json()
    assert body["total_clients"] >= 1
    assert any(t["name"] == "Consultorio Test" for t in body["tenants"])

    mark = platform_client.post(
        f"/api/v1/platform/tenants/{org.id}/mark-paid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mark.status_code == 200
    assert mark.json()["payment_status"] in {"current", "due_soon", "due_today"}


def test_delete_tenant_service():
    org_id = uuid4()
    org = Organization(
        id=org_id,
        name="Consultorio a borrar",
        slug="consultorio-borrar",
        service_started_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        paid_until=date(2026, 6, 1),
        monthly_fee=Decimal("25000"),
    )
    db = MagicMock()
    service = PlatformService(db)
    service.orgs = MagicMock()
    service.orgs.get_by_id.return_value = org

    result = service.delete_tenant(org_id)

    assert "Consultorio a borrar" in result.message
    db.execute.assert_called_once()
    db.commit.assert_called_once()
