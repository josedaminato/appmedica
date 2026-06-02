from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import InsuranceClaimStatus
from app.models.insurance_claim import InsuranceClaim
from app.repositories.health_insurance_repository import HealthInsuranceRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.schemas.health_insurance_analytics import InsuranceRankingItem, InsuranceRankingResponse

MIN_SAMPLE = 3
GOOD_DAYS_THRESHOLD = 45


class HealthInsuranceAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.insurances = HealthInsuranceRepository(db)
        self.claims = InsuranceClaimRepository(db)

    def get_ranking(self, organization_id: uuid.UUID) -> InsuranceRankingResponse:
        catalog = {i.id: i for i in self.insurances.list_all(organization_id)}
        rows = self.claims.list_all_with_insurance(organization_id)

        by_insurance: dict[uuid.UUID, list[tuple[InsuranceClaim, str]]] = defaultdict(list)
        for claim, insurance in rows:
            by_insurance[claim.health_insurance_id].append((claim, insurance.name))

        items: list[InsuranceRankingItem] = []
        for insurance_id, insurance in catalog.items():
            claims = by_insurance.get(insurance_id, [])
            item = self._build_item(insurance_id, insurance.name, claims)
            items.append(item)

        items.sort(
            key=lambda x: (
                x.score is None,
                -(x.score or 0),
                x.avg_days_to_collect if x.avg_days_to_collect is not None else 9999,
            ),
        )
        for rank, item in enumerate(items, start=1):
            item.rank = rank

        return InsuranceRankingResponse(items=items, min_sample=MIN_SAMPLE)

    def _build_item(
        self,
        insurance_id: uuid.UUID,
        name: str,
        claims: list[tuple[InsuranceClaim, str]],
    ) -> InsuranceRankingItem:
        total = len(claims)
        open_statuses = {InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED}
        collected = [
            c for c, _ in claims
            if c.status == InsuranceClaimStatus.COLLECTED and c.collected_at
        ]
        rejected = [c for c, _ in claims if c.status == InsuranceClaimStatus.REJECTED]
        open_claims = [c for c, _ in claims if c.status in open_statuses]

        days_to_collect = [
            (c.collected_at.date() - c.service_date).days
            for c in collected
            if c.collected_at
        ]
        avg_days = statistics.mean(days_to_collect) if days_to_collect else None
        median_days = statistics.median(days_to_collect) if days_to_collect else None

        within_45 = None
        if days_to_collect:
            within_45 = round(
                100.0 * sum(1 for d in days_to_collect if d <= GOOD_DAYS_THRESHOLD) / len(days_to_collect),
                1,
            )

        rejection_rate = round(100.0 * len(rejected) / total, 1) if total else None
        open_debt = sum((c.expected_amount for c in open_claims), Decimal("0"))

        sample_sufficient = len(collected) >= MIN_SAMPLE
        score = self._compute_score(avg_days, rejection_rate, within_45) if sample_sufficient else None
        rating_label = self._rating_label(score, sample_sufficient, total)

        return InsuranceRankingItem(
            health_insurance_id=insurance_id,
            name=name,
            claims_total=total,
            claims_collected=len(collected),
            claims_open=len(open_claims),
            claims_rejected=len(rejected),
            open_debt_total=open_debt,
            avg_days_to_collect=round(avg_days, 1) if avg_days is not None else None,
            median_days_to_collect=float(median_days) if median_days is not None else None,
            pct_collected_within_45_days=within_45,
            rejection_rate_pct=rejection_rate,
            score=score,
            rank=0,
            rating_label=rating_label,
            sample_sufficient=sample_sufficient,
        )

    @staticmethod
    def _compute_score(
        avg_days: float | None,
        rejection_rate: float | None,
        within_45: float | None,
    ) -> float:
        if avg_days is None:
            return 0.0
        score = 100.0
        score -= min(avg_days, 150) * 0.45
        if rejection_rate is not None:
            score -= rejection_rate * 0.35
        if within_45 is not None:
            score += within_45 * 0.15
        return round(max(0.0, min(100.0, score)), 1)

    @staticmethod
    def _rating_label(score: float | None, sample_sufficient: bool, total: int) -> str:
        if total == 0:
            return "Sin datos"
        if not sample_sufficient:
            return "Datos insuficientes"
        if score is None:
            return "Sin datos"
        if score >= 75:
            return "Muy buena"
        if score >= 55:
            return "Aceptable"
        if score >= 35:
            return "Lenta"
        return "Problemática"
