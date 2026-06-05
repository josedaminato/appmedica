import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AppException
from app.models.enums import AppointmentStatus
from app.services.report_service import ReportService


@pytest.fixture
def db():
    return MagicMock()


def test_monthly_report_aggregates(db):
    org_id = uuid.uuid4()
    service = ReportService(db)

    appt_repo = service.appointments
    pay_repo = service.payments
    claim_repo = service.claims

    # Sin organizacion -> zona horaria por defecto (Argentina, UTC-3).
    service.organizations.get_by_id = MagicMock(return_value=None)
    appt_repo.count_between = MagicMock(side_effect=[10, 7, 1, 2])
    pay_repo.sum_paid_between = MagicMock(return_value=(Decimal("50000"), 3))
    claim_repo.sum_collected_between = MagicMock(return_value=(Decimal("120000"), 2))
    claim_repo.count_by_service_date_range = MagicMock(return_value=4)

    report = service.get_monthly_report(org_id, 2026, 6)

    assert report.period_label == "Junio 2026"
    assert report.appointments_total == 10
    assert report.appointments_attended == 7
    assert report.appointments_no_show == 1
    assert report.appointments_cancelled == 2
    assert report.private_collected_total == Decimal("50000")
    assert report.private_payments_count == 3
    assert report.insurance_collected_total == Decimal("120000")
    assert report.total_collected == Decimal("170000")

    # Junio 2026 en hora Argentina (UTC-3): 00:00 local = 03:00 UTC.
    start_dt = datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 7, 1, 3, 0, tzinfo=timezone.utc)
    pay_repo.sum_paid_between.assert_called_once_with(org_id, start_dt, end_dt)
    claim_repo.sum_collected_between.assert_called_once_with(org_id, start_dt, end_dt)
    claim_repo.count_by_service_date_range.assert_called_once_with(
        org_id, date(2026, 6, 1), date(2026, 7, 1),
    )

    appt_repo.count_between.assert_any_call(
        org_id, start_dt, end_dt, status=AppointmentStatus.ATTENDED,
    )


def test_monthly_report_rejects_invalid_month(db):
    service = ReportService(db)
    with pytest.raises(AppException):
        service.get_monthly_report(uuid.uuid4(), 2026, 13)
