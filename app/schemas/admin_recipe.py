from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminRecipeStats(BaseModel):
    likes_count: int = 0
    scrap_count: int = 0


class AdminRecipeIngredient(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
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


class AdminRecipeStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: int
    step_no: int
    instruction: str
    tip: str | None = None
    sort_order: int = 0


class AdminRecipeLabel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label_id: int
    label_type: str
    label_value: str
    source: str
    confidence_score: float | None = None
    sort_order: int = 0


class AdminRecipeNutrition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serving_weight_grams: float | None = None
    kcal_per_serving: int | None = None
    carbohydrate_grams: float | None = None
    protein_grams: float | None = None
    fat_grams: float | None = None
    sodium_milligrams: float | None = None
    source: str
    raw_payload: dict = {}
    updated_at: datetime | None = None


class AdminRecipeClassification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cuisine_type: str | None = None
    dish_type: str | None = None
    cooking_methods: list = []
    meal_types: list = []
    occasions: list = []
    situations: list = []
    main_ingredients: list = []
    taste_keywords: list = []
    texture_keywords: list = []
    diet_keywords: list = []
    allergen_keywords: list = []
    equipment: list = []
    season: list = []
    category_labels: list = []
    classification_source: str
    confidence_score: float | None = None
    updated_at: datetime | None = None


class AdminRecipeMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_id: int
    step_id: int | None = None
    media_type: str
    image_role: str | None = None
    source_url: str | None = None
    storage_url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    storage_provider: str
    generation_id: int | None = None
    is_primary: bool = False
    sort_order: int = 0
    created_at: datetime | None = None


class AdminRecipeListItem(BaseModel):
    recipe_id: int
    title: str
    summary: str | None = None
    servings: float
    cooking_time_minutes: int
    kcal_per_serving: int | None = None
    difficulty: str
    visibility: str
    author_type: str
    source_id: int | None = None
    source_site: str | None = None
    source_recipe_id: str | None = None
    source_record_id: str | None = None
    source_dataset_id: str | None = None
    source_dataset_name: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    likes_count: int = 0
    scrap_count: int = 0
    has_nutrition: bool = False
    has_classification: bool = False
    has_embedding: bool = False

    @classmethod
    def from_model(cls, recipe) -> "AdminRecipeListItem":
        source = recipe.source
        return cls(
            recipe_id=recipe.recipe_id,
            title=recipe.title,
            summary=recipe.summary,
            servings=float(recipe.servings),
            cooking_time_minutes=recipe.cooking_time_minutes,
            kcal_per_serving=recipe.kcal_per_serving,
            difficulty=recipe.difficulty,
            visibility=recipe.visibility,
            author_type=recipe.author_type,
            source_id=recipe.source_id,
            source_site=source.source_site if source else None,
            source_recipe_id=source.source_recipe_id if source else None,
            source_record_id=source.source_record_id if source else None,
            source_dataset_id=source.source_dataset_id if source else None,
            source_dataset_name=source.source_dataset_name if source else None,
            is_active=recipe.is_active,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
            likes_count=recipe.stats.likes_count if recipe.stats else 0,
            scrap_count=recipe.stats.scrap_count if recipe.stats else 0,
            has_nutrition=recipe.nutrition is not None,
            has_classification=recipe.classifications is not None,
            has_embedding=bool(recipe.embeddings),
        )


class AdminRecipeListResponse(BaseModel):
    items: list[AdminRecipeListItem]
    next_cursor: str | None
    has_next: bool


class AdminRecipeDetail(AdminRecipeListItem):
    description: str
    author_id: int | None = None
    source_author_name: str | None = None
    source_author_url: str | None = None
    source_url: str | None = None
    source_organization: str | None = None
    source_license: str | None = None
    source_license_url: str | None = None
    source_published_at: datetime | None = None
    stats: AdminRecipeStats
    ingredients: list[AdminRecipeIngredient] = []
    steps: list[AdminRecipeStep] = []
    labels: list[AdminRecipeLabel] = []
    nutrition: AdminRecipeNutrition | None = None
    classification: AdminRecipeClassification | None = None
    media: list[AdminRecipeMedia] = []

    @classmethod
    def from_model(cls, recipe) -> "AdminRecipeDetail":
        base = AdminRecipeListItem.from_model(recipe).model_dump()
        source = recipe.source
        return cls(
            **base,
            description=recipe.description,
            author_id=recipe.author_id,
            source_author_name=source.source_author_name if source else None,
            source_author_url=source.source_author_url if source else None,
            source_url=source.source_url if source else None,
            source_organization=source.source_organization if source else None,
            source_license=source.source_license if source else None,
            source_license_url=source.source_license_url if source else None,
            source_published_at=source.source_published_at if source else None,
            stats=AdminRecipeStats(
                likes_count=recipe.stats.likes_count if recipe.stats else 0,
                scrap_count=recipe.stats.scrap_count if recipe.stats else 0,
            ),
            ingredients=[
                AdminRecipeIngredient.model_validate(item)
                for item in recipe.ingredients_list
            ],
            steps=[AdminRecipeStep.model_validate(item) for item in recipe.steps],
            labels=[AdminRecipeLabel.model_validate(item) for item in recipe.labels],
            nutrition=(
                AdminRecipeNutrition.model_validate(recipe.nutrition)
                if recipe.nutrition
                else None
            ),
            classification=(
                AdminRecipeClassification.model_validate(recipe.classifications)
                if recipe.classifications
                else None
            ),
            media=[AdminRecipeMedia.model_validate(item) for item in recipe.media],
        )
