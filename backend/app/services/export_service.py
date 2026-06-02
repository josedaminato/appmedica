from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.services.collections_service import CollectionsService
from app.services.patient_service import PatientService
from app.services.report_service import ReportService


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def export_patients(
        self,
        organization_id: uuid.UUID,
        fmt: str,
    ) -> tuple[bytes, str, str]:
        result = PatientService(self.db).list_patients(
            organization_id, page=1, page_size=5000, q=None, is_active=None,
        )
        rows = [
            {
                "apellido": p.last_name,
                "nombre": p.first_name,
                "dni": p.dni,
                "telefono": p.phone or "",
                "email": p.email or "",
                "activo": "si" if p.is_active else "no",
            }
            for p in result.data
        ]
        return self._encode(rows, fmt, "pacientes")

    def export_payments(
        self,
        organization_id: uuid.UUID,
        fmt: str,
    ) -> tuple[bytes, str, str]:
        items = CollectionsService(self.db).list_items(organization_id, "recent")
        rows = [
            {
                "paciente": i.patient_name,
                "fecha": i.service_date.isoformat(),
                "monto": str(i.total_amount),
                "metodo": i.payment_method or "",
                "estado": i.status_label,
            }
            for i in items
        ]
        return self._encode(rows, fmt, "cobros")

    def export_claims(
        self,
        organization_id: uuid.UUID,
        fmt: str,
    ) -> tuple[bytes, str, str]:
        from datetime import date

        from app.repositories.insurance_claim_repository import InsuranceClaimRepository
        from app.repositories.patient_repository import PatientRepository

        repo = InsuranceClaimRepository(self.db)
        patients = PatientRepository(self.db)
        today = date.today()
        rows = []
        for claim, insurance in repo.list_all_with_insurance(organization_id):
            patient = patients.get_by_id(organization_id, claim.patient_id)
            pname = (
                f"{patient.last_name}, {patient.first_name}" if patient else ""
            )
            rows.append(
                {
                    "paciente": pname,
                    "obra_social": insurance.name,
                    "fecha_atencion": claim.service_date.isoformat(),
                    "monto": str(claim.expected_amount),
                    "estado": claim.status.value,
                    "dias_pendiente": str(max(0, (today - claim.service_date).days)),
                },
            )
        return self._encode(rows, fmt, "reclamos-os")

    def export_debt(
        self,
        organization_id: uuid.UUID,
        fmt: str,
    ) -> tuple[bytes, str, str]:
        coll = CollectionsService(self.db)
        private = coll.list_items(organization_id, "private")
        insurance = coll.list_items(organization_id, "insurance")
        rows = []
        for i in private:
            rows.append(
                {
                    "tipo": "particular",
                    "paciente": i.patient_name,
                    "fecha": i.service_date.isoformat(),
                    "total": str(i.total_amount),
                    "pendiente": str(i.balance_pending),
                    "dias": i.days_pending,
                    "estado": i.status_label,
                },
            )
        for i in insurance:
            rows.append(
                {
                    "tipo": "obra_social",
                    "paciente": i.patient_name,
                    "obra_social": i.health_insurance_name or "",
                    "fecha": i.service_date.isoformat(),
                    "total": str(i.total_amount),
                    "pendiente": str(i.balance_pending),
                    "dias": i.days_pending,
                    "estado": i.status_label,
                },
            )
        return self._encode(rows, fmt, "deuda")

    def export_monthly_report(
        self,
        organization_id: uuid.UUID,
        year: int,
        month: int,
        fmt: str,
    ) -> tuple[bytes, str, str]:
        rows = ReportService(self.db).monthly_report_rows(organization_id, year, month)
        basename = f"reporte-{year}-{month:02d}"
        return self._encode(rows, fmt, basename)

    def _encode(
        self, rows: list[dict[str, str]], fmt: str, basename: str,
    ) -> tuple[bytes, str, str]:
        if not rows:
            rows = [{"info": "sin datos"}]
        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            content = buf.getvalue().encode("utf-8-sig")
            return content, "text/csv", f"{basename}.csv"
        if fmt == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = basename[:31]
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h, "") for h in headers])
            buf = io.BytesIO()
            wb.save(buf)
            return (
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"{basename}.xlsx",
            )
        raise bad_request("Formato inválido. Usá xlsx o csv")
