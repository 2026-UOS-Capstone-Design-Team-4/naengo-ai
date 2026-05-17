from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models.user import User, UserProfile
from app.schemas.user import (
    UserInputAppendRequest,
    UserInputDeleteRequest,
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
        return UserProfileResponse(user_input=_latest_first(profile.user_input))

    def append_profile_user_input(
        self,
        user_id: int,
        body: UserInputAppendRequest,
    ) -> UserProfileResponse | None:
        profile = self.get_profile(user_id)
        if not profile:
            return None

        text = _clean_user_input(body.text)
        if text is None:
            return UserProfileResponse(user_input=_latest_first(profile.user_input))

        profile.user_input = [*_clean_user_inputs(profile.user_input), text]
        self.db.commit()
        self.db.refresh(profile)
        return UserProfileResponse(user_input=_latest_first(profile.user_input))

    def delete_profile_user_inputs(
        self,
        user_id: int,
        body: UserInputDeleteRequest,
    ) -> UserProfileResponse | None:
        profile = self.get_profile(user_id)
        if not profile:
            return None

        delete_target = _clean_user_input(body.text)
        current_inputs = _clean_user_inputs(profile.user_input)
        if delete_target is not None:
            try:
                current_inputs.remove(delete_target)
            except ValueError:
                pass
        profile.user_input = current_inputs
        self.db.commit()
        self.db.refresh(profile)
        return UserProfileResponse(user_input=_latest_first(profile.user_input))


def _clean_user_input(value: str) -> str | None:
    text = value.strip()
    return text or None


def _clean_user_inputs(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [
        text
        for value in values
        if isinstance(value, str) and (text := _clean_user_input(value)) is not None
    ]


def _latest_first(values: list[str] | None) -> list[str]:
    return list(reversed(_clean_user_inputs(values)))
