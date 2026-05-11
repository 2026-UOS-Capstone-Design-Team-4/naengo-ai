from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models.user import User, UserProfile
from app.schemas.user import (
    UserInputUpdateRequest,
    UserProfileResponse,
    UserUpdateRequest,
)


class UserUpdateStatus(StrEnum):
    NOT_FOUND = "not_found"
    NICKNAME_DUPLICATED = "nickname_duplicated"
    UPDATED = "updated"


@dataclass
class UserUpdateResult:
    status: UserUpdateStatus
    user: User | None = None


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def update_user(
        self,
        user_id: int,
        body: UserUpdateRequest,
    ) -> UserUpdateResult:
        user = self.get_user(user_id)
        if not user:
            return UserUpdateResult(status=UserUpdateStatus.NOT_FOUND)

        if body.nickname is not None and body.nickname != user.nickname:
            duplicate = (
                self.db.query(User).filter(User.nickname == body.nickname).first()
            )
            if duplicate:
                return UserUpdateResult(
                    status=UserUpdateStatus.NICKNAME_DUPLICATED,
                    user=user,
                )
            user.nickname = body.nickname

        self.db.commit()
        self.db.refresh(user)
        return UserUpdateResult(status=UserUpdateStatus.UPDATED, user=user)

    def get_profile(self, user_id: int) -> UserProfile | None:
        return (
            self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        )

    def get_profile_response(self, user_id: int) -> UserProfileResponse | None:
        profile = self.get_profile(user_id)
        if not profile:
            return None
        return UserProfileResponse(user_input=profile.user_input or [])

    def update_profile(
        self,
        user_id: int,
        body: UserInputUpdateRequest,
    ) -> UserProfileResponse | None:
        profile = self.get_profile(user_id)
        if not profile:
            return None

        profile.user_input = body.user_input
        self.db.commit()
        self.db.refresh(profile)
        return UserProfileResponse(user_input=profile.user_input or [])
