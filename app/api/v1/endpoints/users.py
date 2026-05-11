from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_id
from app.api.v1.docs.users import (
    GET_ME_DESCRIPTION,
    GET_ME_RESPONSES,
    GET_ME_SUMMARY,
    GET_MY_PROFILE_DESCRIPTION,
    GET_MY_PROFILE_RESPONSES,
    GET_MY_PROFILE_SUMMARY,
    GET_MY_SCRAPS_DESCRIPTION,
    GET_MY_SCRAPS_RESPONSES,
    GET_MY_SCRAPS_SUMMARY,
    PATCH_ME_DESCRIPTION,
    PATCH_ME_RESPONSES,
    PATCH_ME_SUMMARY,
    PATCH_MY_PROFILE_DESCRIPTION,
    PATCH_MY_PROFILE_RESPONSES,
    PATCH_MY_PROFILE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.recipe import RecipeListResponse
from app.schemas.user import (
    UserInputUpdateRequest,
    UserProfileResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.recipe_service import RecipeService
from app.services.user_service import UserService, UserUpdateStatus

router = APIRouter()


@router.get(
    "/me",
    summary=GET_ME_SUMMARY,
    description=GET_ME_DESCRIPTION,
    response_model=UserResponse,
    responses=GET_ME_RESPONSES,
)
def get_me(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    user = user_service.get_user(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user


@router.patch(
    "/me",
    summary=PATCH_ME_SUMMARY,
    description=PATCH_ME_DESCRIPTION,
    response_model=UserResponse,
    responses=PATCH_ME_RESPONSES,
)
def update_me(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    result = user_service.update_user(current_user_id, body)
    if result.status == UserUpdateStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if result.status == UserUpdateStatus.NICKNAME_DUPLICATED:
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.")
    return result.user


@router.get(
    "/me/profile",
    summary=GET_MY_PROFILE_SUMMARY,
    description=GET_MY_PROFILE_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=GET_MY_PROFILE_RESPONSES,
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    profile = user_service.get_profile_response(current_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
    return profile


@router.patch(
    "/me/profile",
    summary=PATCH_MY_PROFILE_SUMMARY,
    description=PATCH_MY_PROFILE_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=PATCH_MY_PROFILE_RESPONSES,
)
def update_my_profile(
    body: UserInputUpdateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    profile = user_service.update_profile(current_user_id, body)
    if not profile:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
    return profile


@router.get(
    "/me/scraps",
    summary=GET_MY_SCRAPS_SUMMARY,
    description=GET_MY_SCRAPS_DESCRIPTION,
    response_model=RecipeListResponse,
    responses=GET_MY_SCRAPS_RESPONSES,
)
def get_my_scraps(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    recipe_service = RecipeService(db)
    return recipe_service.get_scraps(current_user_id, cursor, limit)
