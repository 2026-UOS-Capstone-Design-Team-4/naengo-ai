from copy import deepcopy
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

UserRecipeStatus = Literal["PENDING", "APPROVED", "REJECTED"]
UserRecipeImportStatus = Literal["NOT_IMPORTED", "IMPORTED", "FAILED"]

DEFAULT_USER_RECIPE_PAYLOAD = {
    "description": None,
    "ingredients": [],
    "ingredients_raw": [],
    "instructions": [],
    "servings": None,
    "cooking_time_minutes": None,
    "kcal_per_serving": None,
    "difficulty": None,
    "category": [],
    "tags": [],
    "tips": [],
    "video_url": None,
    "image_url": None,
}


def build_user_recipe_payload(values: dict | None = None) -> dict:
    payload = deepcopy(DEFAULT_USER_RECIPE_PAYLOAD)
    if values:
        payload.update(values)
    return payload


class UserRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    submission_text: str = Field(min_length=1)


class UserRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_id: int
    user_id: int
    title: str
    submission_text: str
    draft_payload: dict = Field(default_factory=build_user_recipe_payload)
    ai_suggested_patch: dict = Field(default_factory=build_user_recipe_payload)
    validation_errors: list[dict] = Field(default_factory=list)
    status: str
    import_status: UserRecipeImportStatus = "NOT_IMPORTED"
    is_active: bool = True
    admin_note: str | None = None
    rejection_reason: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    imported_recipe_id: int | None = None
    imported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("draft_payload", "ai_suggested_patch", mode="before")
    @classmethod
    def normalize_payloads(cls, value: dict | None) -> dict:
        return build_user_recipe_payload(value)


class UserRecipeListResponse(BaseModel):
    items: list[UserRecipeResponse]
    next_cursor: str | None
    has_next: bool


class UserRecipeAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    submission_text: str | None = None
    draft_payload: dict | None = None
    ai_suggested_patch: dict | None = None
    validation_errors: list[dict] | None = None
    status: UserRecipeStatus | None = None
    admin_note: str | None = None
    rejection_reason: str | None = None

    @field_validator("draft_payload", "ai_suggested_patch", mode="before")
    @classmethod
    def normalize_payloads(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        return build_user_recipe_payload(value)
