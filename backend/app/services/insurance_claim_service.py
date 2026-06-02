import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.models.enums import InsuranceClaimStatus
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.schemas.common import PaginatedResponse, pagination_meta
from app.schemas.insurance_claim import (
    InsuranceClaimListItem,
    InsuranceClaimResponse,
    InsuranceClaimUpdate,
)


class InsuranceClaimService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = InsuranceClaimRepository(db)

    def list_claims(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        status: InsuranceClaimStatus | None = None,
        health_insurance_id: uuid.UUID | None = None,
        open_only: bool = False,
    ) -> PaginatedResponse[InsuranceClaimListItem]:
        rows, total = self.repo.list_paginated(
            organization_id,
            page=page,
            page_size=page_size,
            status=status,
            health_insurance_id=health_insurance_id,
            open_only=open_only,
        )
        today = date.today()
        items = [
            self._to_list_item(claim, patient, insurance, today)
            for claim, patient, insurance in rows
        ]
        return PaginatedResponse(
            data=items,
            meta=pagination_meta(page, page_size, total),
        )

    def get_claim(
        self, organization_id: uuid.UUID, claim_id: uuid.UUID,
    ) -> InsuranceClaimListItem:
        row = self._get_row(organization_id, claim_id)
        claim, patient, insurance = row
        return self._to_list_item(claim, patient, insurance, date.today())

    def update_claim(
        self,
        organization_id: uuid.UUID,
        claim_id: uuid.UUID,
        data: InsuranceClaimUpdate,
    ) -> InsuranceClaimListItem:
        claim, patient, insurance = self._get_row(organization_id, claim_id)
        updates = data.model_dump(exclude_unset=True)
        now = datetime.now(timezone.utc)

        new_status = updates.get("status")
        if new_status == InsuranceClaimStatus.INVOICED:
            if "invoiced_at" not in updates and claim.invoiced_at is None:
                updates["invoiced_at"] = now
        if new_status == InsuranceClaimStatus.COLLECTED:
            if "collected_at" not in updates and claim.collected_at is None:
                updates["collected_at"] = now
            if claim.invoiced_at is None and updates.get("invoiced_at") is None:
                updates["invoiced_at"] = updates.get("collected_at", now)
        if new_status == InsuranceClaimStatus.REJECTED:
            if claim.collected_at is not None:
                raise bad_request("No se puede rechazar un reclamo ya cobrado")

        if updates.get("collected_at") and new_status is None:
            updates["status"] = InsuranceClaimStatus.COLLECTED
        if updates.get("invoiced_at") and new_status is None and not updates.get("collected_at"):
            if claim.status == InsuranceClaimStatus.PENDING:
                updates["status"] = InsuranceClaimStatus.INVOICED

        for field, value in updates.items():
            setattr(claim, field, value)

        if claim.status == InsuranceClaimStatus.COLLECTED and claim.collected_at is None:
            claim.collected_at = now

        self.repo.update(claim)
        self.db.commit()
        self.db.refresh(claim)
        return self._to_list_item(claim, patient, insurance, date.today())

    def _get_row(self, organization_id: uuid.UUID, claim_id: uuid.UUID) -> tuple:
        row = self.repo.get_with_details(organization_id, claim_id)
        if not row:
            raise not_found("Reclamo")
        return row

    @staticmethod
    def _to_list_item(
        claim,
        patient,
        insurance,
        today: date,
    ) -> InsuranceClaimListItem:
        days_since = (today - claim.service_date).days
        days_to_collect = None
        days_service_to_invoice = None
        if claim.collected_at:
            collected_date = claim.collected_at.date()
            days_to_collect = (collected_date - claim.service_date).days
        if claim.invoiced_at:
            days_service_to_invoice = (claim.invoiced_at.date() - claim.service_date).days

        base = InsuranceClaimResponse.model_validate(claim)
        return InsuranceClaimListItem(
            **base.model_dump(),
            patient_name=f"{patient.last_name}, {patient.first_name}",
            health_insurance_name=insurance.name,
            days_since_service=max(0, days_since),
            days_to_collect=days_to_collect,
            days_service_to_invoice=days_service_to_invoice,
        )
