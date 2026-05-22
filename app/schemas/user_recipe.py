from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRecipeStatus = Literal["PENDING", "APPROVED", "REJECTED"]
UserRecipeImportStatus = Literal["NOT_IMPORTED", "IMPORTED", "FAILED"]


class UserRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    servings: float = Field(gt=0)
    cooking_time_minutes: int = Field(gt=0)
    kcal_per_serving: int | None = Field(default=None, ge=0)
    difficulty: Literal["easy", "normal", "hard"]
    source_url: str | None = None
    ingredients: list["UserRecipeIngredientCreate"] = Field(min_length=1)
    steps: list["UserRecipeStepCreate"] = Field(min_length=1)
    category: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UserRecipeIngredientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_name: str | None = None
    name: str = Field(min_length=1, max_length=100)
    normalized_name: str | None = None
    amount_text: str | None = None
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    raw_text: str | None = None
    is_optional: bool = False


class UserRecipeStepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_no: int = Field(gt=0)
    instruction: str = Field(min_length=1)
    client_image_key: str | None = None
    tip: str | None = None


class UserRecipeIngredientSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_ingredient_id: int | None = None
    group_name: str | None = None
    name: str
    normalized_name: str | None = None
    amount_text: str | None = None
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    raw_text: str | None = None
    is_optional: bool = False
    sort_order: int = 0


class UserRecipeStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_step_id: int | None = None
    step_no: int
    instruction: str
    image_url: str | None = None
    tip: str | None = None
    sort_order: int = 0


class UserRecipeLabelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_label_id: int | None = None
    label_type: str
    label_value: str
    confidence_score: float | None = None
    source: str = "ADMIN"
    sort_order: int = 0


class UserRecipeNutritionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serving_weight_grams: float | None = None
    carbohydrate_grams: float | None = None
    protein_grams: float | None = None
    fat_grams: float | None = None
    sodium_milligrams: float | None = None
    source: str = "ADMIN"
    raw: dict = Field(default_factory=dict)


class UserRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_id: int
    user_id: int
    title: str
    description: str | None = None
    servings: float | None = None
    yield_quantity: float | None = None
    yield_unit: str | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None
    difficulty: str | None = None
    source_url: str | None = None
    main_image_url: str | None = None
    category: list[str] = []
    tags: list[str] = []
    tips: list[str] = []
    ingredients: list[UserRecipeIngredientSchema] = []
    steps: list[UserRecipeStepSchema] = []
    labels: list[UserRecipeLabelSchema] = []
    nutrition: UserRecipeNutritionSchema | None = None
    status: str
    import_status: UserRecipeImportStatus = "NOT_IMPORTED"
    is_active: bool = True
    rejection_reason: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    imported_recipe_id: int | None = None
    imported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserRecipeListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_recipe_id: int
    user_id: int
    title: str
    description: str | None = None
    servings: float | None = None
    yield_quantity: float | None = None
    yield_unit: str | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None
    difficulty: str | None = None
    main_image_url: str | None = None
    category: list[str] = []
    tags: list[str] = []
    status: str
    import_status: UserRecipeImportStatus = "NOT_IMPORTED"
    is_active: bool = True
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class UserRecipeListResponse(BaseModel):
    items: list[UserRecipeResponse]
    next_cursor: str | None
    has_next: bool


class UserRecipeAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    servings: float | None = None
    yield_quantity: float | None = None
    yield_unit: str | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None
    difficulty: str | None = None
    source_url: str | None = None
    main_image_url: str | None = None
    ingredients: list[UserRecipeIngredientSchema] | None = None
    steps: list[UserRecipeStepSchema] | None = None
    labels: list[UserRecipeLabelSchema] | None = None
    nutrition: UserRecipeNutritionSchema | None = None
    status: UserRecipeStatus | None = None
    rejection_reason: str | None = None
