from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _to_str(v: object) -> str:
    return str(v) if not isinstance(v, str) else v


class IngredientItem(BaseModel):
    name: str
    amount: Annotated[str, BeforeValidator(_to_str)]
    unit: str
    type: str
    note: str | None = ""


class RecipeNutritionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serving_weight_grams: float | None = None
    kcal_per_serving: int | None = None
    carbohydrate_grams: float | None = None
    protein_grams: float | None = None
    fat_grams: float | None = None
    sodium_milligrams: float | None = None
    source: Literal["SOURCE", "RULE", "AI", "ADMIN"] = "SOURCE"


class RecipeStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_no: int
    instruction: str
    tip: str | None = None


class RecipeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    ingredients: list[IngredientItem] = []
    ingredients_raw: str
    steps: list[RecipeStepResponse] = []
    servings: float
    cooking_time_minutes: int
    kcal_per_serving: int | None = None
    nutrition: RecipeNutritionResponse | None = None
    difficulty: Literal["easy", "normal", "hard"]
    category: list[str] = []
    tags: list[str] = []
    tips: list[str] = []
    video_url: str | None = None
    image_url: str | None = None


class RecipeSchema(RecipeBase):
    summary: str | None = None
    author_type: Literal["ADMIN", "USER", "SOURCE"] = "ADMIN"


class RecipeResponse(RecipeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="recipe_id")
    author_type: Literal["ADMIN", "USER", "SOURCE"]


class RecipeListItemResponse(RecipeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="recipe_id")
    author_type: Literal["ADMIN", "USER", "SOURCE"]
    created_at: datetime | None = None
    likes_count: int = 0
    scrap_count: int = 0
    is_liked: bool = False
    is_scrapped: bool = False


class RecipeListResponse(BaseModel):
    items: list[RecipeListItemResponse]
    next_cursor: str | None
    has_next: bool


class RecipeStatsResponse(BaseModel):
    likes_count: int
    scrap_count: int
