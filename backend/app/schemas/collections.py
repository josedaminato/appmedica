import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CollectionTab = Literal["private", "insurance", "recent", "pending"]


class CollectionsSummary(BaseModel):
    private_debt_total: Decimal
    insurance_debt_total: Decimal
    payments_today_total: Decimal
    payments_today_count: int
    pending_insurance_claims: int
    unclosed_attended: int
    overdue_unresolved: int


class CollectionRow(BaseModel):
    """Fila unificada para la pantalla Cobros."""

    row_id: str
    kind: Literal["private", "insurance", "payment"]
    patient_id: uuid.UUID
    patient_name: str
    professional_name: str | None = None
    appointment_id: uuid.UUID | None = None
    service_date: date
    health_insurance_name: str | None = None
    status_label: str
    status_code: str
    payment_method: str | None = None
    total_amount: Decimal
    balance_pending: Decimal
    days_pending: int = 0
    can_collect: bool = False
    can_mark_insurance: bool = False
