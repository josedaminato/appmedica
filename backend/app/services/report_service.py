from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.core.timezone import local_date_range_bounds_utc, org_timezone
from app.models.enums import AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.report import MonthlyReport

_MONTH_NAMES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def _month_date_bounds(year: int, month: int) -> tuple[date, date]:
    if month < 1 or month > 12:
        raise bad_request("Mes inválido")
    start_date = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_date_exclusive = start_date + timedelta(days=last_day)
    return start_date, end_date_exclusive


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)
        self.organizations = OrganizationRepository(db)

    def get_monthly_report(
        self,
        organization_id: uuid.UUID,
        year: int,
        month: int,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> MonthlyReport:
        if year < 2000 or year > 2100:
            raise bad_request("Año inválido")

        start_date, end_date_exclusive = _month_date_bounds(year, month)
        tz = org_timezone(self.organizations.get_by_id(organization_id))
        # Mes en hora del consultorio, expresado en limites UTC reales.
        start_dt, end_dt = local_date_range_bounds_utc(start_date, end_date_exclusive, tz)

        appt_total = self.appointments.count_between(
            organization_id, start_dt, end_dt, professional_id=professional_id,
        )
        appt_attended = self.appointments.count_between(
            organization_id, start_dt, end_dt,
            status=AppointmentStatus.ATTENDED,
            professional_id=professional_id,
        )
        appt_no_show = self.appointments.count_between(
            organization_id, start_dt, end_dt,
            status=AppointmentStatus.NO_SHOW,
            professional_id=professional_id,
        )
        appt_cancelled = self.appointments.count_between(
            organization_id, start_dt, end_dt,
            status=AppointmentStatus.CANCELLED,
            professional_id=professional_id,
        )

        if professional_id is not None:
            private_total, private_count = self.payments.sum_paid_between_for_professional(
                organization_id, professional_id, start_dt, end_dt,
            )
        else:
            private_total, private_count = self.payments.sum_paid_between(
                organization_id, start_dt, end_dt,
            )
        insurance_total, insurance_count = self.claims.sum_collected_between(
            organization_id, start_dt, end_dt, professional_id=professional_id,
        )
        insurance_services = self.claims.count_by_service_date_range(
            organization_id, start_date, end_date_exclusive, professional_id=professional_id,
        )

        return MonthlyReport(
            year=year,
            month=month,
            period_label=f"{_MONTH_NAMES[month - 1]} {year}",
            appointments_total=appt_total,
            appointments_attended=appt_attended,
            appointments_no_show=appt_no_show,
            appointments_cancelled=appt_cancelled,
            private_collected_total=private_total,
            private_payments_count=private_count,
            insurance_collected_total=insurance_total,
            insurance_collected_count=insurance_count,
            insurance_services_count=insurance_services,
            total_collected=private_total + insurance_total,
        )

    def monthly_report_rows(
        self,
        organization_id: uuid.UUID,
        year: int,
        month: int,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> list[dict[str, str]]:
        report = self.get_monthly_report(
            organization_id, year, month, professional_id=professional_id,
        )
        return [
            {"concepto": "Período", "valor": report.period_label},
            {"concepto": "Turnos totales", "valor": str(report.appointments_total)},
            {"concepto": "Turnos asistidos", "valor": str(report.appointments_attended)},
            {"concepto": "Ausencias", "valor": str(report.appointments_no_show)},
            {"concepto": "Cancelados", "valor": str(report.appointments_cancelled)},
            {"concepto": "Cobrado particulares", "valor": str(report.private_collected_total)},
            {"concepto": "Pagos particulares (cant.)", "valor": str(report.private_payments_count)},
            {"concepto": "Cobrado obras sociales", "valor": str(report.insurance_collected_total)},
            {"concepto": "Reclamos cobrados (cant.)", "valor": str(report.insurance_collected_count)},
            {"concepto": "Prestaciones OS (mes)", "valor": str(report.insurance_services_count)},
            {"concepto": "Total cobrado", "valor": str(report.total_collected)},
        ]
