from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.openapi.admin_pending_recipes import (
    DELETE_ADMIN_PENDING_RECIPE_DESCRIPTION,
    DELETE_ADMIN_PENDING_RECIPE_RESPONSES,
    DELETE_ADMIN_PENDING_RECIPE_SUMMARY,
    GET_ADMIN_PENDING_RECIPE_DESCRIPTION,
    GET_ADMIN_PENDING_RECIPE_SUMMARY,
    GET_ADMIN_PENDING_RECIPES_DESCRIPTION,
    GET_ADMIN_PENDING_RECIPES_RESPONSES,
    GET_ADMIN_PENDING_RECIPES_SUMMARY,
    PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION,
    PATCH_ADMIN_PENDING_RECIPE_RESPONSES,
    PATCH_ADMIN_PENDING_RECIPE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.pending_recipe import (
    PendingRecipeAdminUpdate,
    PendingRecipeListResponse,
    PendingRecipeResponse,
)
from app.services.pending_recipe_service import (
    PendingRecipeActiveDeleteError,
    PendingRecipeInvalidCursorError,
    PendingRecipeService,
)

router = APIRouter()


@router.get(
    "",
    summary=GET_ADMIN_PENDING_RECIPES_SUMMARY,
    description=GET_ADMIN_PENDING_RECIPES_DESCRIPTION,
    response_model=PendingRecipeListResponse,
    responses=GET_ADMIN_PENDING_RECIPES_RESPONSES,
)
def list_admin_pending_recipes(
    status: Literal["PENDING", "APPROVED", "REJECTED"] | None = Query(
        default=None,
        description="검수 상태로 필터링합니다.",
    ),
    is_active: bool | None = Query(
        default=None,
        description="사용자 삭제 여부를 포함한 활성 상태로 필터링합니다.",
    ),
    user_id: int | None = Query(
        default=None,
        ge=1,
        description="특정 사용자의 제출 레시피만 조회합니다.",
    ),
    q: str | None = Query(
        default=None,
        description="제목과 제출 원문에서 검색할 문자열입니다.",
    ),
    cursor: str | None = Query(
        default=None,
        description="이전 응답의 `next_cursor` 값입니다.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="한 번에 조회할 개수입니다. 최대 100개입니다.",
    ),
    db: Session = Depends(get_db),
):
    service = PendingRecipeService(db)
    try:
        items, next_cursor = service.get_admin_pending_recipes(
            status=status,
            is_active=is_active,
            user_id=user_id,
            q=q,
            cursor=cursor,
            limit=limit,
        )
    except PendingRecipeInvalidCursorError:
        raise ApiError(
            400,
            "INVALID_CURSOR",
            "Cursor is invalid.",
        ) from None
    return PendingRecipeListResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=next_cursor is not None,
    )


@router.get(
    "/{pending_recipe_id}",
    summary=GET_ADMIN_PENDING_RECIPE_SUMMARY,
    description=GET_ADMIN_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
)
def get_admin_pending_recipe(
    pending_recipe_id: int,
    db: Session = Depends(get_db),
):
    pending = PendingRecipeService(db).get_active_pending_recipe(pending_recipe_id)
    if not pending:
        raise ApiError(
            404,
            "PENDING_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return pending


@router.delete(
    "/{pending_recipe_id}",
    summary=DELETE_ADMIN_PENDING_RECIPE_SUMMARY,
    description=DELETE_ADMIN_PENDING_RECIPE_DESCRIPTION,
    responses=DELETE_ADMIN_PENDING_RECIPE_RESPONSES,
)
def hard_delete_inactive_pending_recipe(
    pending_recipe_id: int,
    db: Session = Depends(get_db),
):
    pending_recipe_service = PendingRecipeService(db)
    try:
        deleted = pending_recipe_service.hard_delete_inactive_pending_recipe(
            pending_recipe_id,
        )
    except PendingRecipeActiveDeleteError:
        raise ApiError(
            409,
            "PENDING_RECIPE_ACTIVE",
            "Active pending recipe cannot be hard-deleted.",
        ) from None

    if not deleted:
        raise ApiError(
            404,
            "PENDING_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return {"message": "제출 레시피가 삭제되었습니다."}


@router.patch(
    "/{pending_recipe_id}",
    summary=PATCH_ADMIN_PENDING_RECIPE_SUMMARY,
    description=PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=PATCH_ADMIN_PENDING_RECIPE_RESPONSES,
)
def update_pending_recipe_status(
    pending_recipe_id: int,
    body: PendingRecipeAdminUpdate,
    db: Session = Depends(get_db),
):
    pending_recipe_service = PendingRecipeService(db)
    pending = pending_recipe_service.update_pending_recipe_status(
        pending_recipe_id,
        body,
    )

    if not pending:
        raise ApiError(
            404,
            "PENDING_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return pending
