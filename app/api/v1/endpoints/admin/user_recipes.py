from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.openapi.admin_user_recipes import (
    DELETE_ADMIN_USER_RECIPE_DESCRIPTION,
    DELETE_ADMIN_USER_RECIPE_RESPONSES,
    DELETE_ADMIN_USER_RECIPE_SUMMARY,
    GET_ADMIN_USER_RECIPE_DESCRIPTION,
    GET_ADMIN_USER_RECIPE_SUMMARY,
    GET_ADMIN_USER_RECIPES_DESCRIPTION,
    GET_ADMIN_USER_RECIPES_RESPONSES,
    GET_ADMIN_USER_RECIPES_SUMMARY,
    PATCH_ADMIN_USER_RECIPE_DESCRIPTION,
    PATCH_ADMIN_USER_RECIPE_RESPONSES,
    PATCH_ADMIN_USER_RECIPE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.user_recipe import (
    UserRecipeAdminUpdate,
    UserRecipeListResponse,
    UserRecipeResponse,
)
from app.services.user_recipe_service import (
    UserRecipeActiveDeleteError,
    UserRecipeInvalidCursorError,
    UserRecipeService,
)

router = APIRouter()


@router.get(
    "",
    summary=GET_ADMIN_USER_RECIPES_SUMMARY,
    description=GET_ADMIN_USER_RECIPES_DESCRIPTION,
    response_model=UserRecipeListResponse,
    responses=GET_ADMIN_USER_RECIPES_RESPONSES,
)
def list_admin_user_recipes(
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
    service = UserRecipeService(db)
    try:
        items, next_cursor = service.get_admin_user_recipes(
            status=status,
            is_active=is_active,
            user_id=user_id,
            q=q,
            cursor=cursor,
            limit=limit,
        )
    except UserRecipeInvalidCursorError:
        raise ApiError(
            400,
            "INVALID_CURSOR",
            "Cursor is invalid.",
        ) from None
    return UserRecipeListResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=next_cursor is not None,
    )


@router.get(
    "/{user_recipe_id}",
    summary=GET_ADMIN_USER_RECIPE_SUMMARY,
    description=GET_ADMIN_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
)
def get_admin_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
):
    recipe = UserRecipeService(db).get_active_user_recipe(user_recipe_id)
    if not recipe:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return recipe


@router.delete(
    "/{user_recipe_id}",
    summary=DELETE_ADMIN_USER_RECIPE_SUMMARY,
    description=DELETE_ADMIN_USER_RECIPE_DESCRIPTION,
    responses=DELETE_ADMIN_USER_RECIPE_RESPONSES,
)
def hard_delete_inactive_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
):
    service = UserRecipeService(db)
    try:
        deleted = service.hard_delete_inactive_user_recipe(user_recipe_id)
    except UserRecipeActiveDeleteError:
        raise ApiError(
            409,
            "USER_RECIPE_ACTIVE",
            "Active user recipe cannot be hard-deleted.",
        ) from None

    if not deleted:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return {"message": "제출 레시피가 삭제되었습니다."}


@router.patch(
    "/{user_recipe_id}",
    summary=PATCH_ADMIN_USER_RECIPE_SUMMARY,
    description=PATCH_ADMIN_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
    responses=PATCH_ADMIN_USER_RECIPE_RESPONSES,
)
def update_user_recipe_status(
    user_recipe_id: int,
    body: UserRecipeAdminUpdate,
    db: Session = Depends(get_db),
):
    recipe = UserRecipeService(db).update_user_recipe_status(user_recipe_id, body)
    if not recipe:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return recipe
