from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.recipe import IngredientItem

PendingRecipeStatus = Literal["PENDING", "APPROVED", "REJECTED"]


class PendingRecipeCreate(BaseModel):
    title: str
    content: str
    description: str | None = None
    ingredients: list[IngredientItem] | None = None
    ingredients_raw: str | None = None
    instructions: list[str] | None = None
    servings: float | None = None
    cooking_time: int | None = None
    calories: int | None = None
    difficulty: Literal["easy", "normal", "hard"] | None = None
    category: list[str] | None = None
    tags: list[str] | None = None
    tips: list[str] | None = None
    video_url: str | None = None
    image_url: str | None = None


class PendingRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pending_recipe_id: int
    title: str
    content: str
    description: str | None = None
    ingredients: list[IngredientItem] | None = None
    ingredients_raw: str | None = None
    instructions: list[str] | None = None
    servings: float | None = None
    cooking_time: int | None = None
    calories: int | None = None
    difficulty: Literal["easy", "normal", "hard"] | None = None
    category: list[str] | None = None
    tags: list[str] | None = None
    tips: list[str] | None = None
    video_url: str | None = None
    image_url: str | None = None
    status: str
    admin_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class PendingRecipeAdminUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    description: str | None = None
    ingredients: list[IngredientItem] | None = None
    ingredients_raw: str | None = None
    instructions: list[str] | None = None
    servings: float | None = None
    cooking_time: int | None = None
    calories: int | None = None
    difficulty: Literal["easy", "normal", "hard"] | None = None
    category: list[str] | None = None
    tags: list[str] | None = None
    tips: list[str] | None = None
    video_url: str | None = None
    image_url: str | None = None
    status: PendingRecipeStatus | None = None
    admin_note: str | None = None
