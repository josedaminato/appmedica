import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import resolve_professional_filter
from app.schemas.collections import CollectionRow, CollectionTab, CollectionsSummary
from app.services.collections_service import CollectionsService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/summary", response_model=CollectionsSummary)
def get_collections_summary(
    current_user: CurrentUser,
    db: DbSession,
) -> CollectionsSummary:
    return CollectionsService(db).get_summary(current_user.organization_id)


@router.get("/items", response_model=list[CollectionRow])
def list_collection_items(
    current_user: CurrentUser,
    db: DbSession,
    tab: CollectionTab = Query("pending"),
    professional_id: uuid.UUID | None = Query(None),
) -> list[CollectionRow]:
    prof_filter = resolve_professional_filter(current_user, professional_id)
    return CollectionsService(db).list_items(
        current_user.organization_id,
        tab,
        professional_id=prof_filter,
    )
