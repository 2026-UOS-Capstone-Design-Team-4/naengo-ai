from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    nickname: str
    role: str
    is_active: bool
    is_blocked: bool
    created_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_input: list[str] = []


class UserUpdateRequest(BaseModel):
    nickname: str | None = None


class UserInputUpdateRequest(BaseModel):
    user_input: list[str]
