from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "error"}
