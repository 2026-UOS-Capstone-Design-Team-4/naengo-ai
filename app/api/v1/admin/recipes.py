from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.recipe import Recipe

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "",
    summary="video_url로 레시피 조회",
    description="video_url을 쿼리 파라미터로 전달하면 해당 레시피의 전체 정보를 반환합니다. 레시피 등록 전 중복 여부 확인에 사용합니다.",
)
def get_recipe_by_video_url(video_url: str, db: Session = Depends(get_db)):
    recipe = db.scalar(select(Recipe).where(Recipe.video_url == video_url))
    if not recipe:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")
    return {
        "id": recipe.recipe_id,
        "title": recipe.title,
        "description": recipe.description,
        "ingredients": recipe.ingredients,
        "ingredients_raw": recipe.ingredients_raw,
        "instructions": recipe.instructions,
        "servings": recipe.servings,
        "cooking_time": recipe.cooking_time,
        "calories": recipe.calories,
        "difficulty": recipe.difficulty,
        "category": recipe.category,
        "tags": recipe.tags,
        "tips": recipe.tips,
        "content": recipe.content,
        "video_url": recipe.video_url,
        "image_url": recipe.image_url,
        "is_active": recipe.is_active,
        "author_type": recipe.author_type,
        "created_at": recipe.created_at,
    }
