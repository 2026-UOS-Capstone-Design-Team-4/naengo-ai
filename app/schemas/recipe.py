from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IngredientItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_name: str | None = None
    name: str
    amount_text: str | None = None
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    raw_text: str | None = None
    is_optional: bool = False


class RecipeStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_no: int
    instruction: str
    image_url: str | None = None
    tip: str | None = None


class RecipeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="recipe_id")
    title: str
    summary: str | None = None
    servings: float
    cooking_time_minutes: int
    kcal_per_serving: int | None = None
    difficulty: Literal["easy", "normal", "hard"]
    main_image_url: str | None = None
    category: list[str] = []
    tags: list[str] = []


class RecipeSchema(RecipeBase):
    author_type: Literal["ADMIN", "USER", "SOURCE"] = "ADMIN"


class RecipeListItemResponse(RecipeBase):
    created_at: datetime | None = None
    likes_count: int = 0
    scrap_count: int = 0
    is_liked: bool = False
    is_scrapped: bool = False


class RecipeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="recipe_id")
    title: str
    summary: str | None = None
    description: str
    servings: float
    cooking_time_minutes: int
    kcal_per_serving: int | None = None
    difficulty: Literal["easy", "normal", "hard"]
    author_type: Literal["ADMIN", "USER", "SOURCE"]
    main_image_url: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    category: list[str] = []
    tags: list[str] = []
    tips: list[str] = []
    warnings: list[str] = []
    ingredients: list[IngredientItem] = []
    steps: list[RecipeStepResponse] = []
    likes_count: int = 0
    scrap_count: int = 0
    is_liked: bool = False
    is_scrapped: bool = False


RecipeResponse = RecipeDetailResponse


class RecipeListResponse(BaseModel):
    items: list[RecipeListItemResponse]
    next_cursor: str | None
    has_next: bool


class RecipeStatsResponse(BaseModel):
    likes_count: int
    scrap_count: int
