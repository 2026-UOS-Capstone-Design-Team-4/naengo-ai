from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.admin_recipes import (
    GET_ADMIN_RECIPE_DESCRIPTION,
    GET_ADMIN_RECIPE_RESPONSES,
    GET_ADMIN_RECIPE_SUMMARY,
    GET_ADMIN_RECIPES_DESCRIPTION,
    GET_ADMIN_RECIPES_RESPONSES,
    GET_ADMIN_RECIPES_SUMMARY,
)
from app.db.session import get_db
from app.schemas.admin_recipe import (
    AdminRecipeDetail,
    AdminRecipeListItem,
    AdminRecipeListResponse,
)
from app.services.admin_recipe_service import (
    AdminRecipeInvalidCursorError,
    AdminRecipeNotFoundError,
    AdminRecipeService,
)

router = APIRouter()


@router.get(
    "",
    summary=GET_ADMIN_RECIPES_SUMMARY,
    description=GET_ADMIN_RECIPES_DESCRIPTION,
    response_model=AdminRecipeListResponse,
    responses=GET_ADMIN_RECIPES_RESPONSES,
)
def list_admin_recipes(
    sort: Literal["latest", "likes", "scraps"] = Query(
        default="latest",
        description="정렬 기준입니다. `latest`, `likes`, `scraps`를 지원합니다.",
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
    is_active: bool | None = Query(
        default=None,
        description="서비스 노출 활성 여부로 필터링합니다.",
    ),
    source_site: str | None = Query(
        default=None,
        description="원천 사이트로 필터링합니다. 예: `10000recipe`, `foodsafetykorea`",
    ),
    author_type: Literal["ADMIN", "USER", "SOURCE"] | None = Query(
        default=None,
        description="레시피 작성 주체로 필터링합니다.",
    ),
    visibility: Literal["PUBLIC", "ADMIN_ONLY"] | None = Query(
        default=None,
        description="레시피 공개 범위로 필터링합니다.",
    ),
    difficulty: Literal["easy", "normal", "hard"] | None = Query(
        default=None,
        description=(
            "요리 난이도로 필터링합니다. `easy`, `normal`, `hard`를 지원합니다."
        ),
    ),
    q: str | None = Query(
        default=None,
        description=(
            "레시피 제목에 포함된 문자열로 부분 검색합니다. "
            "예: `김치`, `육회`, `한우 육회`. "
            "빈 문자열이거나 전달하지 않으면 검색 필터를 적용하지 않습니다."
        ),
        examples=["김치", "육회", "한우 육회"],
    ),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    try:
        recipes, next_cursor = AdminRecipeService(db).get_recipes(
            sort=sort,
            cursor=cursor,
            limit=limit,
            is_active=is_active,
            source_site=source_site,
            author_type=author_type,
            visibility=visibility,
            difficulty=difficulty,
            q=q,
        )
    except AdminRecipeInvalidCursorError:
        raise ApiError(
            400,
            "INVALID_CURSOR",
            "Cursor is invalid.",
        ) from None
    return AdminRecipeListResponse(
        items=[AdminRecipeListItem.from_model(recipe) for recipe in recipes],
        next_cursor=str(next_cursor) if next_cursor else None,
        has_next=next_cursor is not None,
    )


@router.get(
    "/{recipe_id}",
    summary=GET_ADMIN_RECIPE_SUMMARY,
    description=GET_ADMIN_RECIPE_DESCRIPTION,
    response_model=AdminRecipeDetail,
    responses=GET_ADMIN_RECIPE_RESPONSES,
)
def get_admin_recipe(
    recipe_id: int = Path(description="조회할 정식 레시피 ID입니다.", ge=1),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    try:
        recipe = AdminRecipeService(db).get_recipe(recipe_id)
    except AdminRecipeNotFoundError:
        raise ApiError(
            404,
            "RECIPE_NOT_FOUND",
            "Recipe was not found.",
        ) from None
    return AdminRecipeDetail.from_model(recipe)
