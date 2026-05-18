from copy import deepcopy
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PendingRecipeStatus = Literal["PENDING", "APPROVED", "REJECTED"]
PendingRecipeImportStatus = Literal["NOT_IMPORTED", "IMPORTED", "FAILED"]

DEFAULT_PENDING_RECIPE_PAYLOAD = {
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


def build_pending_recipe_payload(values: dict | None = None) -> dict:
    payload = deepcopy(DEFAULT_PENDING_RECIPE_PAYLOAD)
    if values:
        payload.update(values)
    return payload


class PendingRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    submission_text: str = Field(min_length=1)


class PendingRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pending_recipe_id: int
    user_id: int
    title: str
    submission_text: str
    draft_payload: dict = Field(default_factory=build_pending_recipe_payload)
    ai_suggested_patch: dict = Field(default_factory=build_pending_recipe_payload)
    validation_errors: list[dict] = Field(default_factory=list)
    status: str
    import_status: PendingRecipeImportStatus = "NOT_IMPORTED"
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
        return build_pending_recipe_payload(value)


class PendingRecipeListResponse(BaseModel):
    items: list[PendingRecipeResponse]
    next_cursor: str | None
    has_next: bool


class PendingRecipeAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    submission_text: str | None = None
    draft_payload: dict | None = None
    ai_suggested_patch: dict | None = None
    validation_errors: list[dict] | None = None
    status: PendingRecipeStatus | None = None
    admin_note: str | None = None
    rejection_reason: str | None = None

    @field_validator("draft_payload", "ai_suggested_patch", mode="before")
    @classmethod
    def normalize_payloads(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        return build_pending_recipe_payload(value)
