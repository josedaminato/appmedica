from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health_check(db: DbSession) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "database": "ok"})
    except Exception:
        return JSONResponse(
            {"status": "degraded", "database": "error"},
            status_code=503,
        )
