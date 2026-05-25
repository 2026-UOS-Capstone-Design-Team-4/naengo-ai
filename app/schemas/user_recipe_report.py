from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRecipeReportReason = Literal[
    "INAPPROPRIATE",
    "COPYRIGHT",
    "SPAM",
    "DANGEROUS",
    "FALSE_INFO",
    "OTHER",
]
UserRecipeReportStatus = Literal["PENDING", "REVIEWING", "RESOLVED", "REJECTED"]


class UserRecipeReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: UserRecipeReportReason
    description: str | None = Field(default=None, max_length=1000)


class UserRecipeReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    user_recipe_id: int
    reporter_user_id: int
    recipe_owner_user_id: int
    reason: UserRecipeReportReason
    description: str | None = None
    status: UserRecipeReportStatus
    review_note: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserRecipeReportListResponse(BaseModel):
    items: list[UserRecipeReportResponse]
    next_cursor: str | None
    has_next: bool


class UserRecipeReportAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: UserRecipeReportStatus | None = None
    review_note: str | None = Field(default=None, max_length=1000)
