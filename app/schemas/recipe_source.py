from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SourceType = Literal[
    "INTERNAL",
    "USER_SUBMISSION",
    "WEB_SCRAPE",
    "VIDEO",
    "EXTERNAL_API",
    "PUBLIC_DATA",
]
ParserType = Literal["MANUAL", "HTML", "AI", "API", "DATASET"]
ParseStatus = Literal["NOT_PARSED", "PARSED", "INVALID", "DUPLICATE", "REVIEW_REQUIRED"]
ReviewStatus = Literal["PENDING", "APPROVED", "REJECTED"]
ImportStatus = Literal["NOT_IMPORTED", "IMPORTED", "FAILED"]
Difficulty = Literal["easy", "normal", "hard"]


class ExtractedIngredient(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extracted_ingredient_id: int | None = None
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


class ExtractedStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extracted_step_id: int | None = None
    step_no: int
    instruction: str
    source_image_url: str | None = None
    tip: str | None = None
    raw_text: str | None = None
    sort_order: int = 0


class ExtractedLabel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extracted_label_id: int | None = None
    label_type: Literal["TAG", "TIP", "CATEGORY", "WARNING"]
    label_value: str
    confidence_score: float | None = None
    source: Literal["SCRAPE", "RULE", "AI", "ADMIN"] = "ADMIN"
    sort_order: int = 0


class RecipeSourceQualityScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completeness_score: float | None = None
    parse_confidence: float | None = None
    ingredient_confidence: float | None = None
    metadata_confidence: float | None = None
    rewrite_confidence: float | None = None
    nutrition_confidence: float | None = None
    duplicate_score: float | None = None
    estimated_fields: list[str] = []
    validation_summary: list[dict] = []
    quality_notes: dict = {}


class RecipeSourceExtractionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extraction_id: int | None = None
    title: str
    summary: str | None = None
    description: str | None = None
    servings: float | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None
    serving_weight_grams: float | None = None
    carbohydrate_grams: float | None = None
    protein_grams: float | None = None
    fat_grams: float | None = None
    sodium_milligrams: float | None = None
    nutrition_source: Literal["SOURCE", "RULE", "AI", "ADMIN"] | None = None
    nutrition_raw: dict = {}
    difficulty: Difficulty | None = None
    source_main_image_url: str | None = None
    source_thumbnail_url: str | None = None
    source_video_url: str | None = None
    content_hash: str | None = None
    quality_score: RecipeSourceQualityScoreSchema | None = None
    ingredients: list[ExtractedIngredient] = []
    steps: list[ExtractedStep] = []
    labels: list[ExtractedLabel] = []


class RecipeSourceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: int
    source_site: str
    source_type: SourceType
    parser_type: ParserType
    source_url: str | None
    source_record_id: str | None = None
    source_organization: str | None = None
    source_dataset_id: str | None = None
    source_dataset_name: str | None = None
    title: str | None = None
    parse_status: ParseStatus
    review_status: ReviewStatus
    import_status: ImportStatus
    collected_at: datetime
    has_errors: bool = False

    @classmethod
    def from_model(cls, obj: Any) -> "RecipeSourceListItem":
        return cls(
            source_id=obj.source_id,
            source_site=obj.source_site,
            source_type=obj.source_type,
            parser_type=obj.parser_type,
            source_url=obj.source_url,
            source_record_id=obj.source_record_id,
            source_organization=obj.source_organization,
            source_dataset_id=obj.source_dataset_id,
            source_dataset_name=obj.source_dataset_name,
            title=obj.extraction.title if obj.extraction else None,
            parse_status=obj.parse_status,
            review_status=obj.review_status,
            import_status=obj.import_status,
            collected_at=obj.collected_at,
            has_errors=bool(obj.validation_errors),
        )


class RecipeSourceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: int
    source_type: SourceType
    source_site: str
    parser_type: ParserType
    source_recipe_id: str | None
    source_url: str | None
    source_record_id: str | None
    source_organization: str | None
    source_dataset_id: str | None
    source_dataset_name: str | None
    source_api_url: str | None
    source_license: str | None
    source_license_url: str | None
    source_author_name: str | None
    source_author_url: str | None
    source_published_at: datetime | None
    raw_payload: dict
    raw_content_hash: str | None
    parse_status: ParseStatus
    review_status: ReviewStatus
    import_status: ImportStatus
    validation_errors: list
    extraction_version: str | None
    collected_at: datetime
    parsed_at: datetime | None
    reviewed_at: datetime | None
    imported_at: datetime | None
    imported_recipe_id: int | None
    extraction: RecipeSourceExtractionSchema | None = None
    created_at: datetime
    updated_at: datetime


class RecipeSourceUpdate(BaseModel):
    extraction: RecipeSourceExtractionSchema | None = None
    validation_errors: list[dict] | None = None
    parse_status: ParseStatus | None = None
    review_status: ReviewStatus | None = None


class RecipeSourceRejectRequest(BaseModel):
    reason: str


class RecipeSourceListResponse(BaseModel):
    items: list[RecipeSourceListItem]
    next_cursor: str | None
    has_next: bool
