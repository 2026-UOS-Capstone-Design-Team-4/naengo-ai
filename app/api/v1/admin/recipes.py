from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recipe import Recipe
from app.api.v1.docs.examples import RECIPE_EXAMPLE
from app.schemas.recipe import RecipeResponse

router = APIRouter()


@router.get(
    "",
    summary="video_url로 레시피 조회",
    description=(
        "`video_url` 쿼리 파라미터로 레시피를 조회합니다.\n\n"
        "레시피 등록 전 중복 여부 확인에 사용합니다."
    ),
    response_model=RecipeResponse,
    responses={
        200: {
            "description": "레시피 상세 정보",
            "content": {"application/json": {"example": RECIPE_EXAMPLE}},
        },
        404: {"description": "레시피를 찾을 수 없습니다."},
    },
)
def get_recipe_by_video_url(video_url: str, db: Session = Depends(get_db)):
    recipe = db.scalar(select(Recipe).where(Recipe.video_url == video_url))
    if not recipe:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")
    return RecipeResponse.model_validate(recipe)
