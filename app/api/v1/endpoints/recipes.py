from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_id
from app.api.v1.docs.recipes import (
    DELETE_LIKE_DESCRIPTION,
    DELETE_LIKE_RESPONSES,
    DELETE_LIKE_SUMMARY,
    DELETE_SCRAP_DESCRIPTION,
    DELETE_SCRAP_RESPONSES,
    DELETE_SCRAP_SUMMARY,
    GET_RECIPE_DESCRIPTION,
    GET_RECIPE_RESPONSES,
    GET_RECIPE_SUMMARY,
    GET_RECIPES_DESCRIPTION,
    GET_RECIPES_RESPONSES,
    GET_RECIPES_SUMMARY,
    POST_LIKE_DESCRIPTION,
    POST_LIKE_RESPONSES,
    POST_LIKE_SUMMARY,
    POST_SCRAP_DESCRIPTION,
    POST_SCRAP_RESPONSES,
    POST_SCRAP_SUMMARY,
)
from app.db.session import get_db
from app.schemas.recipe import (
    RecipeListItemResponse,
    RecipeListResponse,
    RecipeStatsResponse,
)
from app.services.recipe_service import (
    AlreadyLikedError,
    AlreadyScrappedError,
    NotLikedError,
    NotScrappedError,
    RecipeNotFoundError,
    RecipeService,
)

router = APIRouter()

_NOT_FOUND = "레시피를 찾을 수 없습니다."


@router.get(
    "",
    summary=GET_RECIPES_SUMMARY,
    description=GET_RECIPES_DESCRIPTION,
    response_model=RecipeListResponse,
    responses=GET_RECIPES_RESPONSES,
)
def get_recipes(
    sort: Literal["latest", "likes"] = Query(default="latest"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    service = RecipeService(db)
    if sort == "likes":
        return service.get_recipes_by_likes(current_user_id, cursor, limit)
    return service.get_recipes_by_latest(current_user_id, cursor, limit)


@router.get(
    "/{recipe_id}",
    summary=GET_RECIPE_SUMMARY,
    description=GET_RECIPE_DESCRIPTION,
    response_model=RecipeListItemResponse,
    responses=GET_RECIPE_RESPONSES,
)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return RecipeService(db).get_recipe(recipe_id, current_user_id)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None


@router.post(
    "/{recipe_id}/likes",
    summary=POST_LIKE_SUMMARY,
    description=POST_LIKE_DESCRIPTION,
    response_model=RecipeStatsResponse,
    responses=POST_LIKE_RESPONSES,
)
def like_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return RecipeService(db).like(recipe_id, current_user_id)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except AlreadyLikedError:
        raise HTTPException(
            status_code=409, detail="이미 좋아요를 눌렀습니다."
        ) from None


@router.delete(
    "/{recipe_id}/likes",
    summary=DELETE_LIKE_SUMMARY,
    description=DELETE_LIKE_DESCRIPTION,
    response_model=RecipeStatsResponse,
    responses=DELETE_LIKE_RESPONSES,
)
def unlike_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return RecipeService(db).unlike(recipe_id, current_user_id)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except NotLikedError:
        raise HTTPException(
            status_code=409, detail="좋아요를 누르지 않았습니다."
        ) from None


@router.post(
    "/{recipe_id}/scraps",
    summary=POST_SCRAP_SUMMARY,
    description=POST_SCRAP_DESCRIPTION,
    response_model=RecipeStatsResponse,
    responses=POST_SCRAP_RESPONSES,
)
def scrap_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return RecipeService(db).scrap(recipe_id, current_user_id)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except AlreadyScrappedError:
        raise HTTPException(
            status_code=409, detail="이미 스크랩한 레시피입니다."
        ) from None


@router.delete(
    "/{recipe_id}/scraps",
    summary=DELETE_SCRAP_SUMMARY,
    description=DELETE_SCRAP_DESCRIPTION,
    response_model=RecipeStatsResponse,
    responses=DELETE_SCRAP_RESPONSES,
)
def unscrap_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return RecipeService(db).unscrap(recipe_id, current_user_id)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except NotScrappedError:
        raise HTTPException(
            status_code=409, detail="스크랩하지 않은 레시피입니다."
        ) from None
