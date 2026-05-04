from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.docs.pending_recipes import (
    DELETE_PENDING_RECIPE_DESCRIPTION,
    DELETE_PENDING_RECIPE_RESPONSES,
    DELETE_PENDING_RECIPE_SUMMARY,
    GET_PENDING_RECIPE_DESCRIPTION,
    GET_PENDING_RECIPE_RESPONSES,
    GET_PENDING_RECIPE_SUMMARY,
    GET_PENDING_RECIPES_DESCRIPTION,
    GET_PENDING_RECIPES_RESPONSES,
    GET_PENDING_RECIPES_SUMMARY,
    POST_PENDING_RECIPE_DESCRIPTION,
    POST_PENDING_RECIPE_RESPONSES,
    POST_PENDING_RECIPE_SUMMARY,
)
from app.core.config import TEMP_USER_ID
from app.db.session import get_db
from app.models.recipe import PendingRecipe
from app.models.user import User
from app.schemas.pending_recipe import PendingRecipeCreate, PendingRecipeResponse

router = APIRouter()


@router.get(
    "",
    summary=GET_PENDING_RECIPES_SUMMARY,
    description=GET_PENDING_RECIPES_DESCRIPTION,
    response_model=list[PendingRecipeResponse],
    responses=GET_PENDING_RECIPES_RESPONSES,
)
def get_pending_recipes(db: Session = Depends(get_db)):
    return (
        db.query(PendingRecipe)
        .filter(PendingRecipe.user_id == TEMP_USER_ID, PendingRecipe.is_active == True)  # noqa: E712
        .order_by(PendingRecipe.created_at.desc())
        .all()
    )


@router.get(
    "/{pending_recipe_id}",
    summary=GET_PENDING_RECIPE_SUMMARY,
    description=GET_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=GET_PENDING_RECIPE_RESPONSES,
)
def get_pending_recipe(pending_recipe_id: int, db: Session = Depends(get_db)):
    pending = (
        db.query(PendingRecipe)
        .filter(
            PendingRecipe.pending_recipe_id == pending_recipe_id,
            PendingRecipe.user_id == TEMP_USER_ID,
            PendingRecipe.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not pending:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")
    return pending


@router.post(
    "",
    summary=POST_PENDING_RECIPE_SUMMARY,
    description=POST_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=POST_PENDING_RECIPE_RESPONSES,
    status_code=201,
)
def create_pending_recipe(body: PendingRecipeCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == TEMP_USER_ID).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    pending = PendingRecipe(
        user_id=TEMP_USER_ID,
        title=body.title,
        content=body.content,
        description=body.description,
        ingredients=[i.model_dump() for i in body.ingredients] if body.ingredients else None,
        ingredients_raw=body.ingredients_raw,
        instructions=body.instructions,
        servings=body.servings,
        cooking_time=body.cooking_time,
        calories=body.calories,
        difficulty=body.difficulty,
        category=body.category,
        tags=body.tags,
        tips=body.tips,
        video_url=body.video_url,
        image_url=body.image_url,
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending


@router.delete(
    "/{pending_recipe_id}",
    summary=DELETE_PENDING_RECIPE_SUMMARY,
    description=DELETE_PENDING_RECIPE_DESCRIPTION,
    responses=DELETE_PENDING_RECIPE_RESPONSES,
)
def delete_pending_recipe(pending_recipe_id: int, db: Session = Depends(get_db)):
    pending = (
        db.query(PendingRecipe)
        .filter(
            PendingRecipe.pending_recipe_id == pending_recipe_id,
            PendingRecipe.user_id == TEMP_USER_ID,
            PendingRecipe.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not pending:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

    pending.is_active = False
    db.commit()
    return {"message": "레시피가 삭제되었습니다."}
