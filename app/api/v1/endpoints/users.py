from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.users import (
    DELETE_MY_PROFILE_USER_INPUT_DESCRIPTION,
    DELETE_MY_PROFILE_USER_INPUT_RESPONSES,
    DELETE_MY_PROFILE_USER_INPUT_SUMMARY,
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
    POST_MY_PROFILE_USER_INPUT_DESCRIPTION,
    POST_MY_PROFILE_USER_INPUT_RESPONSES,
    POST_MY_PROFILE_USER_INPUT_SUMMARY,
)
from app.db.session import get_db
from app.schemas.recipe import RecipeListResponse
from app.schemas.user import (
    UserInputAppendRequest,
    UserInputDeleteRequest,
    UserProfileResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.recipe_service import RecipeService
from app.services.user_profile_input_service import (
    UserProfileInputNormalizeError,
    user_profile_input_normalizer,
)
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
        raise ApiError(404, "RESOURCE_NOT_FOUND", "사용자를 찾을 수 없습니다.")
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
        raise ApiError(404, "RESOURCE_NOT_FOUND", "사용자를 찾을 수 없습니다.")
    if result.status == UserUpdateStatus.NICKNAME_DUPLICATED:
        raise ApiError(409, "CONFLICT", "이미 사용 중인 닉네임입니다.")
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
        raise ApiError(404, "RESOURCE_NOT_FOUND", "프로필을 찾을 수 없습니다.")
    return profile


@router.post(
    "/me/profile",
    summary=POST_MY_PROFILE_USER_INPUT_SUMMARY,
    description=POST_MY_PROFILE_USER_INPUT_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=POST_MY_PROFILE_USER_INPUT_RESPONSES,
)
def append_my_profile_user_input(
    body: UserInputAppendRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    if user_service.get_profile(current_user_id) is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "프로필을 찾을 수 없습니다.")

    try:
        normalized = user_profile_input_normalizer.normalize(body.text)
    except UserProfileInputNormalizeError as exc:
        raise ApiError(
            502,
            "UPSTREAM_ERROR",
            "프로필 입력 문장을 정리하지 못했습니다.",
        ) from exc
    if not normalized.is_user_info or normalized.normalized_sentence is None:
        raise ApiError(
            422,
            "PROFILE_INPUT_NOT_USER_INFO",
            "저장할 수 있는 사용자 정보 문장이 아닙니다.",
            {"reason": normalized.reason},
        )

    profile = user_service.append_profile_user_input(
        current_user_id,
        UserInputAppendRequest(text=normalized.normalized_sentence),
    )
    return profile


@router.delete(
    "/me/profile",
    summary=DELETE_MY_PROFILE_USER_INPUT_SUMMARY,
    description=DELETE_MY_PROFILE_USER_INPUT_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=DELETE_MY_PROFILE_USER_INPUT_RESPONSES,
)
def delete_my_profile_user_inputs(
    body: UserInputDeleteRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user_service = UserService(db)
    profile = user_service.delete_profile_user_inputs(current_user_id, body)
    if not profile:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "프로필을 찾을 수 없습니다.")
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
