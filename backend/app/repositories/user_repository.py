import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.organization))
            .where(User.id == user_id)
        )
        return self.db.scalars(stmt).first()

    def get_by_calendar_feed_token(self, token: str) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.organization))
            .where(
                User.calendar_feed_token == token,
                User.is_active.is_(True),
            )
        )
        return self.db.scalars(stmt).first()

    def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.organization))
            .where(User.email == email.lower())
        )
        return self.db.scalars(stmt).first()

    def list_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[User]:
        stmt = select(User).where(User.organization_id == organization_id)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.order_by(User.full_name.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id_in_organization(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User | None:
        stmt = select(User).where(
            User.organization_id == organization_id,
            User.id == user_id,
        )
        return self.db.scalars(stmt).first()

    def count_by_role(
        self,
        organization_id: uuid.UUID,
        role,
        *,
        active_only: bool = False,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(User).where(
            User.organization_id == organization_id,
            User.role == role,
        )
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        return self.db.scalar(stmt) or 0

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
