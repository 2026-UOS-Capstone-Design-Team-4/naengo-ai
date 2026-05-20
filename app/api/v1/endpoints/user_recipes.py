from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.user_recipes import (
    DELETE_USER_RECIPE_DESCRIPTION,
    DELETE_USER_RECIPE_RESPONSES,
    DELETE_USER_RECIPE_SUMMARY,
    GET_USER_RECIPE_DESCRIPTION,
    GET_USER_RECIPE_RESPONSES,
    GET_USER_RECIPE_SUMMARY,
    GET_USER_RECIPES_DESCRIPTION,
    GET_USER_RECIPES_RESPONSES,
    GET_USER_RECIPES_SUMMARY,
    POST_USER_RECIPE_DESCRIPTION,
    POST_USER_RECIPE_RESPONSES,
    POST_USER_RECIPE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.user_recipe import UserRecipeCreate, UserRecipeResponse
from app.services.user_recipe_service import UserRecipeService

router = APIRouter()


@router.get(
    "",
    summary=GET_USER_RECIPES_SUMMARY,
    description=GET_USER_RECIPES_DESCRIPTION,
    response_model=list[UserRecipeResponse],
    responses=GET_USER_RECIPES_RESPONSES,
)
def get_user_recipes(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return UserRecipeService(db).get_user_recipes(current_user_id)


@router.get(
    "/{user_recipe_id}",
    summary=GET_USER_RECIPE_SUMMARY,
    description=GET_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
    responses=GET_USER_RECIPE_RESPONSES,
)
def get_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    recipe = UserRecipeService(db).get_user_recipe(user_recipe_id, current_user_id)
    if not recipe:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return recipe


@router.post(
    "",
    summary=POST_USER_RECIPE_SUMMARY,
    description=POST_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
    responses=POST_USER_RECIPE_RESPONSES,
    status_code=201,
)
def create_user_recipe(
    body: UserRecipeCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    recipe = UserRecipeService(db).create_user_recipe(body, current_user_id)
    if not recipe:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "사용자를 찾을 수 없습니다.")
    return recipe


@router.delete(
    "/{user_recipe_id}",
    summary=DELETE_USER_RECIPE_SUMMARY,
    description=DELETE_USER_RECIPE_DESCRIPTION,
    responses=DELETE_USER_RECIPE_RESPONSES,
)
def delete_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    deleted = UserRecipeService(db).delete_user_recipe(user_recipe_id, current_user_id)
    if not deleted:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return {"message": "레시피가 삭제되었습니다."}
