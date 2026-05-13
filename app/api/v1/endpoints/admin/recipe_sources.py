import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.recipe_source import (
    RecipeSourceDetail,
    RecipeSourceListItem,
    RecipeSourceListResponse,
    RecipeSourceRejectRequest,
    RecipeSourceUpdate,
)
from app.services.recipe_import_service import RecipeImportService
from app.services.recipe_source_service import (
    RecipeSourceInvalidStatusError,
    RecipeSourceNotFoundError,
    RecipeSourceService,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_SOURCE_NOT_FOUND = "소스를 찾을 수 없습니다."


@router.get("", response_model=RecipeSourceListResponse)
def list_recipe_sources(
    collection_status: str | None = None,
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
        collection_status=collection_status,
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


@router.get("/{source_id}", response_model=RecipeSourceDetail)
def get_recipe_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.get_source(source_id)
    except RecipeSourceNotFoundError:
        raise HTTPException(status_code=404, detail=_SOURCE_NOT_FOUND) from None
    return RecipeSourceDetail.model_validate(source)


@router.patch("/{source_id}", response_model=RecipeSourceDetail)
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
        raise HTTPException(status_code=404, detail=_SOURCE_NOT_FOUND) from None
    return RecipeSourceDetail.model_validate(source)


@router.post("/{source_id}/approve", response_model=RecipeSourceDetail)
def approve_recipe_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    service = RecipeSourceService(db)
    try:
        source = service.approve_source(source_id)
    except RecipeSourceNotFoundError:
        raise HTTPException(status_code=404, detail=_SOURCE_NOT_FOUND) from None
    except RecipeSourceInvalidStatusError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RecipeSourceDetail.model_validate(source)


@router.post("/{source_id}/reject", response_model=RecipeSourceDetail)
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
        raise HTTPException(status_code=404, detail=_SOURCE_NOT_FOUND) from None
    except RecipeSourceInvalidStatusError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RecipeSourceDetail.model_validate(source)


@router.post("/{source_id}/import", status_code=202)
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
        raise HTTPException(status_code=404, detail=_SOURCE_NOT_FOUND) from None

    if source.review_status != "APPROVED" or source.import_status != "NOT_IMPORTED":
        raise HTTPException(
            status_code=409,
            detail=(
                "APPROVED + NOT_IMPORTED 상태인 소스만 import할 수 있습니다. "
                f"현재: review_status={source.review_status}, "
                f"import_status={source.import_status}"
            ),
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
