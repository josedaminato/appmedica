import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.core.rbac import assert_owner
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationSettingsResponse, OrganizationSettingsUpdate
from app.services.organization_settings_propagation import (
    propagate_appointment_duration,
    propagate_private_session_amount,
)


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orgs = OrganizationRepository(db)

    def get_settings(self, organization_id: uuid.UUID) -> OrganizationSettingsResponse:
        org = self._get_org(organization_id)
        return OrganizationSettingsResponse.model_validate(org)

    def update_settings(
        self,
        current_user: User,
        data: OrganizationSettingsUpdate,
    ) -> OrganizationSettingsResponse:
        assert_owner(current_user)
        org = self._get_org(current_user.organization_id)
        old_duration = org.default_appointment_duration_minutes
        old_amount = org.default_private_session_amount

        org.default_appointment_duration_minutes = data.default_appointment_duration_minutes
        org.default_private_session_amount = data.default_private_session_amount
        self.orgs.update(org)

        amounts_updated = propagate_private_session_amount(
            self.db,
            org.id,
            old_amount,
            data.default_private_session_amount,
        )
        durations_updated = propagate_appointment_duration(
            self.db,
            org.id,
            old_duration,
            data.default_appointment_duration_minutes,
        )

        self.db.commit()
        self.db.refresh(org)
        return OrganizationSettingsResponse(
            default_appointment_duration_minutes=org.default_appointment_duration_minutes,
            default_private_session_amount=org.default_private_session_amount,
            future_private_amounts_updated=amounts_updated,
            future_durations_updated=durations_updated,
        )

    def _get_org(self, organization_id: uuid.UUID) -> Organization:
        org = self.db.get(Organization, organization_id)
        if not org:
            raise not_found("Consultorio")
        return org
