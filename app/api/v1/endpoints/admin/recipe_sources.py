import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.recipe_sources import (
    APPROVE_RECIPE_SOURCE_DESCRIPTION,
    APPROVE_RECIPE_SOURCE_RESPONSES,
    APPROVE_RECIPE_SOURCE_SUMMARY,
    GET_RECIPE_SOURCE_DESCRIPTION,
    GET_RECIPE_SOURCE_RESPONSES,
    GET_RECIPE_SOURCE_SUMMARY,
    GET_RECIPE_SOURCES_DESCRIPTION,
    GET_RECIPE_SOURCES_RESPONSES,
    GET_RECIPE_SOURCES_SUMMARY,
    IMPORT_RECIPE_SOURCE_DESCRIPTION,
    IMPORT_RECIPE_SOURCE_RESPONSES,
    IMPORT_RECIPE_SOURCE_SUMMARY,
    PATCH_RECIPE_SOURCE_DESCRIPTION,
    PATCH_RECIPE_SOURCE_RESPONSES,
    PATCH_RECIPE_SOURCE_SUMMARY,
    REJECT_RECIPE_SOURCE_DESCRIPTION,
    REJECT_RECIPE_SOURCE_RESPONSES,
    REJECT_RECIPE_SOURCE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.recipe_source import (
    RecipeSourceDetail,
    RecipeSourceListItem,
    RecipeSourceListResponse,
    RecipeSourceRejectRequest,
    RecipeSourceUpdate,
)
from app.services.ingestion.recipe_import_service import RecipeImportService
from app.services.ingestion.recipe_source_service import (
    RecipeSourceInvalidStatusError,
    RecipeSourceNotFoundError,
    RecipeSourceService,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_SOURCE_NOT_FOUND = "소스를 찾을 수 없습니다."


@router.get(
    "",
    summary=GET_RECIPE_SOURCES_SUMMARY,
    description=GET_RECIPE_SOURCES_DESCRIPTION,
    response_model=RecipeSourceListResponse,
    responses=GET_RECIPE_SOURCES_RESPONSES,
)
def list_recipe_sources(
    parse_status: str | None = None,
    review_status: str | None = None,
    import_status: str | None = None,
    source_site: str | None = None,
    cursor: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    items, next_cursor = service.get_sources(
        parse_status=parse_status,
        review_status=review_status,
        import_status=import_status,
        source_site=source_site,
        cursor=cursor,
        limit=limit,
    )
    return RecipeSourceListResponse(
        items=[RecipeSourceListItem.from_model(item) for item in items],
        next_cursor=str(next_cursor) if next_cursor else None,
        has_next=next_cursor is not None,
    )


@router.get(
    "/{source_id}",
    summary=GET_RECIPE_SOURCE_SUMMARY,
    description=GET_RECIPE_SOURCE_DESCRIPTION,
    response_model=RecipeSourceDetail,
    responses=GET_RECIPE_SOURCE_RESPONSES,
)
def get_recipe_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.get_source(source_id)
    except RecipeSourceNotFoundError:
        raise ApiError(404, "RECIPE_SOURCE_NOT_FOUND", _SOURCE_NOT_FOUND) from None
    return RecipeSourceDetail.model_validate(source)


@router.patch(
    "/{source_id}",
    summary=PATCH_RECIPE_SOURCE_SUMMARY,
    description=PATCH_RECIPE_SOURCE_DESCRIPTION,
    response_model=RecipeSourceDetail,
    responses=PATCH_RECIPE_SOURCE_RESPONSES,
)
def update_recipe_source(
    source_id: int,
    body: RecipeSourceUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.update_source(source_id, body)
    except RecipeSourceNotFoundError:
        raise ApiError(404, "RECIPE_SOURCE_NOT_FOUND", _SOURCE_NOT_FOUND) from None
    return RecipeSourceDetail.model_validate(source)


@router.post(
    "/{source_id}/approve",
    summary=APPROVE_RECIPE_SOURCE_SUMMARY,
    description=APPROVE_RECIPE_SOURCE_DESCRIPTION,
    response_model=RecipeSourceDetail,
    responses=APPROVE_RECIPE_SOURCE_RESPONSES,
)
def approve_recipe_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.approve_source(source_id)
    except RecipeSourceNotFoundError:
        raise ApiError(404, "RECIPE_SOURCE_NOT_FOUND", _SOURCE_NOT_FOUND) from None
    except RecipeSourceInvalidStatusError as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    return RecipeSourceDetail.model_validate(source)


@router.post(
    "/{source_id}/reject",
    summary=REJECT_RECIPE_SOURCE_SUMMARY,
    description=REJECT_RECIPE_SOURCE_DESCRIPTION,
    response_model=RecipeSourceDetail,
    responses=REJECT_RECIPE_SOURCE_RESPONSES,
)
def reject_recipe_source(
    source_id: int,
    body: RecipeSourceRejectRequest,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.reject_source(source_id, body.reason)
    except RecipeSourceNotFoundError:
        raise ApiError(404, "RECIPE_SOURCE_NOT_FOUND", _SOURCE_NOT_FOUND) from None
    except RecipeSourceInvalidStatusError as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    return RecipeSourceDetail.model_validate(source)


@router.post(
    "/{source_id}/import",
    summary=IMPORT_RECIPE_SOURCE_SUMMARY,
    description=IMPORT_RECIPE_SOURCE_DESCRIPTION,
    status_code=202,
    responses=IMPORT_RECIPE_SOURCE_RESPONSES,
)
def import_recipe_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.get_source(source_id)
    except RecipeSourceNotFoundError:
        raise ApiError(404, "RECIPE_SOURCE_NOT_FOUND", _SOURCE_NOT_FOUND) from None

    if source.review_status != "APPROVED" or source.import_status != "NOT_IMPORTED":
        raise ApiError(
            409,
            "RECIPE_SOURCE_NOT_IMPORTABLE",
            "APPROVED + NOT_IMPORTED 상태인 소스만 import할 수 있습니다.",
            {
                "current": {
                    "review_status": source.review_status,
                    "import_status": source.import_status,
                },
                "required": {
                    "review_status": "APPROVED",
                    "import_status": "NOT_IMPORTED",
                },
            },
        )

    background_tasks.add_task(_run_import, source_id)
    return {"status": "accepted", "source_id": source_id}


def _run_import(source_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        RecipeImportService(db).import_source(source_id)
    except Exception as exc:
        logger.error("import 실패: source_id=%d, error=%s", source_id, exc)
    finally:
        db.close()
