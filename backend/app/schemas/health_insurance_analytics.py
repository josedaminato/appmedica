import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class InsuranceRankingItem(BaseModel):
    health_insurance_id: uuid.UUID
    name: str
    claims_total: int
    claims_collected: int
    claims_open: int
    claims_rejected: int
    open_debt_total: Decimal
    avg_days_to_collect: float | None = None
    median_days_to_collect: float | None = None
    pct_collected_within_45_days: float | None = None
    rejection_rate_pct: float | None = None
    score: float | None = None
    rank: int
    rating_label: str
    sample_sufficient: bool = Field(
        description="True si hay al menos min_sample cobros para estadísticas fiables",
    )


class InsuranceRankingResponse(BaseModel):
    items: list[InsuranceRankingItem]
    min_sample: int = 3
    period_note: str = "Basado en todos los reclamos registrados en tu consultorio."
