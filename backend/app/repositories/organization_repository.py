from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Organization)

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        return self.db.scalars(stmt).first()

    def create(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        return organization

    def update(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        return organization
