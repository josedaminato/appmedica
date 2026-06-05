from fastapi import APIRouter
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.calendar import CalendarFeedResponse
from app.services.calendar_feed_service import CalendarFeedService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/feed", response_model=CalendarFeedResponse)
def get_calendar_feed_info(current_user: CurrentUser, db: DbSession) -> CalendarFeedResponse:
    """URL secreta para suscribir el calendario externo (Google, Outlook, Apple)."""
    info = CalendarFeedService(db).get_feed_info(current_user)
    return CalendarFeedResponse(**info)


@router.post("/feed/regenerate", response_model=CalendarFeedResponse)
def regenerate_calendar_feed(current_user: CurrentUser, db: DbSession) -> CalendarFeedResponse:
    """Invalida el enlace anterior y genera uno nuevo."""
    info = CalendarFeedService(db).regenerate_feed_token(current_user)
    return CalendarFeedResponse(**info)


@router.get("/feed/{token}")
def subscribe_calendar_feed(token: str, db: DbSession) -> Response:
    """Feed iCal público (solo lectura). El token es el secreto."""
    body, filename = CalendarFeedService(db).build_feed_for_token(token)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )
