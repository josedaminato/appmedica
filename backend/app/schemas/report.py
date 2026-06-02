from decimal import Decimal

from pydantic import BaseModel, Field


class MonthlyReport(BaseModel):
    year: int
    month: int
    period_label: str
    appointments_total: int
    appointments_attended: int
    appointments_no_show: int
    appointments_cancelled: int
    private_collected_total: Decimal
    private_payments_count: int
    insurance_collected_total: Decimal
    insurance_collected_count: int
    insurance_services_count: int = Field(
        description="Prestaciones OS con fecha de atención en el mes",
    )
    total_collected: Decimal
