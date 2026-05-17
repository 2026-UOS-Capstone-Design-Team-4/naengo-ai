from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.pending_recipes import (
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
from app.db.session import get_db
from app.schemas.pending_recipe import PendingRecipeCreate, PendingRecipeResponse
from app.services.pending_recipe_service import PendingRecipeService

router = APIRouter()


@router.get(
    "",
    summary=GET_PENDING_RECIPES_SUMMARY,
    description=GET_PENDING_RECIPES_DESCRIPTION,
    response_model=list[PendingRecipeResponse],
    responses=GET_PENDING_RECIPES_RESPONSES,
)
def get_pending_recipes(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    pending_recipe_service = PendingRecipeService(db)
    return pending_recipe_service.get_user_pending_recipes(current_user_id)


@router.get(
    "/{pending_recipe_id}",
    summary=GET_PENDING_RECIPE_SUMMARY,
    description=GET_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=GET_PENDING_RECIPE_RESPONSES,
)
def get_pending_recipe(
    pending_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    pending_recipe_service = PendingRecipeService(db)
    pending = pending_recipe_service.get_user_pending_recipe(
        pending_recipe_id,
        current_user_id,
    )
    if not pending:
        raise ApiError(
            404,
            "PENDING_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return pending


@router.post(
    "",
    summary=POST_PENDING_RECIPE_SUMMARY,
    description=POST_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=POST_PENDING_RECIPE_RESPONSES,
    status_code=201,
)
def create_pending_recipe(
    body: PendingRecipeCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    pending_recipe_service = PendingRecipeService(db)
    pending = pending_recipe_service.create_pending_recipe(body, current_user_id)
    if not pending:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "사용자를 찾을 수 없습니다.")
    return pending


@router.delete(
    "/{pending_recipe_id}",
    summary=DELETE_PENDING_RECIPE_SUMMARY,
    description=DELETE_PENDING_RECIPE_DESCRIPTION,
    responses=DELETE_PENDING_RECIPE_RESPONSES,
)
def delete_pending_recipe(
    pending_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    pending_recipe_service = PendingRecipeService(db)
    deleted = pending_recipe_service.delete_user_pending_recipe(
        pending_recipe_id,
        current_user_id,
    )
    if not deleted:
        raise ApiError(
            404,
            "PENDING_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return {"message": "레시피가 삭제되었습니다."}
