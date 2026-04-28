from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recipe import Recipe
from app.api.v1.docs.examples import RECIPE_EXAMPLE
from app.schemas.recipe import RecipeResponse

router = APIRouter()


@router.get(
    "",
    summary="레시피 ID 목록으로 조회",
    description="쿼리 파라미터 `ids`에 레시피 ID를 하나 이상 전달하면 해당 레시피 목록을 반환합니다. (예: `?ids=1&ids=2`)",
    response_model=list[RecipeResponse],
    responses={
        200: {
            "description": "레시피 목록",
            "content": {"application/json": {"example": [RECIPE_EXAMPLE]}},
        }
    },
)
async def get_recipes_by_ids(
    ids: list[int] = Query(),
    db: Session = Depends(get_db),
):
    recipes = db.query(Recipe).filter(Recipe.recipe_id.in_(ids), Recipe.is_active == True).all()  # noqa: E712
    return recipes
