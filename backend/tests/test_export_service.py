"""Tests de ExportService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.enums import InsuranceClaimStatus
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.patient import Patient
from app.services.export_service import ExportService


def _claim_row() -> tuple[InsuranceClaim, Patient, HealthInsurance]:
    org_id = uuid4()
    patient = Patient(
        id=uuid4(),
        organization_id=org_id,
        first_name="Juan",
        last_name="Perez",
        dni="30123456",
        is_active=True,
    )
    insurance = HealthInsurance(
        id=uuid4(),
        organization_id=org_id,
        name="Sancor",
    )
    claim = InsuranceClaim(
        id=uuid4(),
        organization_id=org_id,
        patient_id=patient.id,
        health_insurance_id=insurance.id,
        appointment_id=None,
        service_date=date(2026, 5, 15),
        expected_amount=Decimal("15000"),
        status=InsuranceClaimStatus.PENDING,
    )
    return claim, patient, insurance


def test_export_claims_uses_single_repository_query():
    org_id = uuid4()
    service = ExportService(MagicMock())
    claim, patient, insurance = _claim_row()

    mock_repo = MagicMock()
    mock_repo.list_all_with_insurance_and_patient.return_value = [
        (claim, patient, insurance),
    ]

    with patch(
        "app.repositories.insurance_claim_repository.InsuranceClaimRepository",
        return_value=mock_repo,
    ):
        content, media, filename = service.export_claims(org_id, "csv")

    mock_repo.list_all_with_insurance_and_patient.assert_called_once_with(org_id)
    assert b"Perez, Juan" in content
    assert b"Sancor" in content
    assert media == "text/csv"
    assert filename == "reclamos-os.csv"
