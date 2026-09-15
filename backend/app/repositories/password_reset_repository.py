from datetime import datetime, timezone
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.password_reset import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PasswordResetToken)

    def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        return self.db.scalars(stmt).first()

    def invalidate_unused_for_user(self, user_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        self.db.execute(stmt)

    def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.flush()
        return token
