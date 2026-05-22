from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    email: str | None
    created_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str | None
    nickname: str
    role: str
    is_active: bool
    is_blocked: bool
    user_identities: list[UserIdentityResponse]
    created_at: datetime
    updated_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_input: list[str] = []


class UserUpdateRequest(BaseModel):
    nickname: str | None = None


class UserInputAppendRequest(BaseModel):
    text: str = Field(min_length=1)


class UserInputDeleteRequest(BaseModel):
    text: str = Field(min_length=1)
