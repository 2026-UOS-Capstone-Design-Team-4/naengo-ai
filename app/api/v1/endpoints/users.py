from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.docs.users import (
    GET_ME_DESCRIPTION,
    GET_ME_RESPONSES,
    GET_ME_SUMMARY,
    GET_MY_PROFILE_DESCRIPTION,
    GET_MY_PROFILE_RESPONSES,
    GET_MY_PROFILE_SUMMARY,
    PATCH_ME_DESCRIPTION,
    PATCH_ME_RESPONSES,
    PATCH_ME_SUMMARY,
    PATCH_MY_PROFILE_DESCRIPTION,
    PATCH_MY_PROFILE_RESPONSES,
    PATCH_MY_PROFILE_SUMMARY,
)
from app.core.config import TEMP_USER_ID
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.schemas.user import (
    UserInputUpdateRequest,
    UserProfileResponse,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter()


@router.get(
    "/me",
    summary=GET_ME_SUMMARY,
    description=GET_ME_DESCRIPTION,
    response_model=UserResponse,
    responses=GET_ME_RESPONSES,
)
def get_me(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == TEMP_USER_ID).first()
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
def update_me(body: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == TEMP_USER_ID).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if body.nickname is not None and body.nickname != user.nickname:
        duplicate = db.query(User).filter(User.nickname == body.nickname).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.")
        user.nickname = body.nickname

    db.commit()
    db.refresh(user)
    return user


@router.get(
    "/me/profile",
    summary=GET_MY_PROFILE_SUMMARY,
    description=GET_MY_PROFILE_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=GET_MY_PROFILE_RESPONSES,
)
def get_my_profile(db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == TEMP_USER_ID).first()
    if not profile:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
    return UserProfileResponse(user_input=profile.user_input or [])


@router.patch(
    "/me/profile",
    summary=PATCH_MY_PROFILE_SUMMARY,
    description=PATCH_MY_PROFILE_DESCRIPTION,
    response_model=UserProfileResponse,
    responses=PATCH_MY_PROFILE_RESPONSES,
)
def update_my_profile(body: UserInputUpdateRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == TEMP_USER_ID).first()
    if not profile:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")

    profile.user_input = body.user_input
    db.commit()
    db.refresh(profile)
    return UserProfileResponse(user_input=profile.user_input or [])
