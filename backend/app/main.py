import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.db.session import SessionLocal
from app.services.daily_agenda_digest_service import DailyAgendaDigestService
from app.services.reminder_service import ReminderService

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

_is_production = settings.is_production


async def _daily_agenda_digest_loop() -> None:
    interval = max(300, settings.daily_agenda_digest_check_interval_seconds)
    while True:
        await asyncio.sleep(interval)
        if not settings.daily_agenda_digest_enabled:
            continue
        db = SessionLocal()
        try:
            result = await DailyAgendaDigestService(db, settings).process_all_organizations()
            if result["sent"]:
                logger.info("Resúmenes de agenda enviados: %s", result["sent"])
        except Exception:
            logger.exception("Error en resumen diario de agenda")
        finally:
            db.close()


async def _reminder_processor_loop() -> None:
    interval = max(30, settings.reminder_processor_interval_seconds)
    while True:
        await asyncio.sleep(interval)
        if not settings.reminders_enabled:
            continue
        db = SessionLocal()
        try:
            result = await ReminderService(db, settings).process_due_jobs()
            if result["processed"]:
                logger.info(
                    "Recordatorios procesados: %s enviados, %s fallidos",
                    result["sent"],
                    result["failed"],
                )
        except Exception:
            logger.exception("Error en procesador de recordatorios")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks: list[asyncio.Task] = []
    if settings.reminders_enabled and settings.reminder_background_loop:
        tasks.append(asyncio.create_task(_reminder_processor_loop()))
        logger.info("Procesador de recordatorios iniciado (cada %ss)", settings.reminder_processor_interval_seconds)
    if settings.daily_agenda_digest_enabled:
        tasks.append(asyncio.create_task(_daily_agenda_digest_loop()))
        logger.info(
            "Resumen diario de agenda activo (revisa cada %ss, envío ~%02d:%02d hora del consultorio)",
            settings.daily_agenda_digest_check_interval_seconds,
            settings.daily_agenda_digest_hour,
            settings.daily_agenda_digest_minute,
        )
    yield
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": detail.get("code", "ERROR"), "message": detail.get("message", "")}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Datos inválidos",
                "details": exc.errors(),
            }
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs"}


app.include_router(api_router, prefix="/api/v1")
