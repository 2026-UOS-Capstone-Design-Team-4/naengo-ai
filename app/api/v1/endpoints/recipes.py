from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.docs.examples import RECIPE_EXAMPLE
from app.api.v1.docs.recipes import (
    GET_RECIPES_DESCRIPTION,
    GET_RECIPES_RESPONSES,
    GET_RECIPES_SUMMARY,
)
from app.db.session import get_db
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeListResponse, RecipeResponse
from app.services.recipe_service import RecipeService

router = APIRouter()


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
):
    service = RecipeService(db)
    if sort == "likes":
        return service.get_recipes_by_likes(cursor, limit)
    return service.get_recipes_by_latest(cursor, limit)


@router.get(
    "/by-ids",
    summary="레시피 ID 목록으로 조회",
    description=(
        "쿼리 파라미터 `ids`에 레시피 ID를 하나 이상 전달하면 "
        "해당 레시피 목록을 반환합니다. (예: `?ids=1&ids=2`)"
    ),
    response_model=list[RecipeResponse],
    responses={
        200: {
            "description": "레시피 목록",
            "content": {"application/json": {"example": [RECIPE_EXAMPLE]}},
        }
    },
)
def get_recipes_by_ids(
    ids: list[int] = Query(),
    db: Session = Depends(get_db),
):
    recipes = (
        db.query(Recipe)
        .filter(Recipe.recipe_id.in_(ids), Recipe.is_active.is_(True))
        .all()
    )
    return recipes
