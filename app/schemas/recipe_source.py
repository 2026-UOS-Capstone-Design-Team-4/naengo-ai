from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SourceType = Literal[
    "INTERNAL",
    "USER_SUBMISSION",
    "WEB_SCRAPE",
    "VIDEO",
    "EXTERNAL_API",
]
ParserType = Literal["MANUAL", "HTML", "AI", "API"]
CollectionStatus = Literal["COLLECTED", "FAILED", "SKIPPED"]
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
    title: str | None = None
    instruction: str
    duration_minutes: int | None = None
    temperature: str | None = None
    equipment: list[str] = []
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


class RecipeSourceExtractionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extraction_id: int | None = None
    title: str
    subtitle: str | None = None
    summary: str | None = None
    description: str | None = None
    servings: float | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None
    calories: int | None = None
    difficulty: Difficulty | None = None
    difficulty_score: int | None = None
    source_main_image_url: str | None = None
    source_thumbnail_url: str | None = None
    source_video_url: str | None = None
    content_hash: str | None = None
    completeness_score: float | None = None
    confidence_score: float | None = None
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
    title: str | None = None
    collection_status: CollectionStatus
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
            title=obj.extraction.title if obj.extraction else None,
            collection_status=obj.collection_status,
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
    source_author_name: str | None
    source_author_url: str | None
    source_published_at: datetime | None
    raw_payload: dict
    raw_content_hash: str | None
    collection_status: CollectionStatus
    parse_status: ParseStatus
    review_status: ReviewStatus
    import_status: ImportStatus
    validation_errors: list
    parser_version: str | None
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
