from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.models.recipe_source import (
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedLabel,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
    RecipeSourceQualityScore,
)
from app.schemas.recipe_source import RecipeSourceUpdate
from app.services.ingestion.recipe_classification_service import (
    recipe_classification_service,
)


class RecipeSourceNotFoundError(Exception):
    pass


class RecipeSourceInvalidStatusError(Exception):
    pass


VALID_DIFFICULTIES = {"easy", "normal", "hard"}


class RecipeSourceService:
    def __init__(self, db: Session):
        self.db = db

    def get_sources(
        self,
        parse_status: str | None = None,
        review_status: str | None = None,
        import_status: str | None = None,
        source_site: str | None = None,
        cursor: int | None = None,
        limit: int = 20,
    ) -> tuple[list[RecipeSource], int | None]:
        query = self.db.query(RecipeSource).options(
            joinedload(RecipeSource.extraction)
        )

        if parse_status:
            query = query.filter(RecipeSource.parse_status == parse_status)
        if review_status:
            query = query.filter(RecipeSource.review_status == review_status)
        if import_status:
            query = query.filter(RecipeSource.import_status == import_status)
        if source_site:
            query = query.filter(RecipeSource.source_site == source_site)
        if cursor:
            query = query.filter(RecipeSource.source_id < cursor)

        rows = query.order_by(RecipeSource.source_id.desc()).limit(limit + 1).all()
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = items[-1].source_id if has_next else None
        return items, next_cursor

    def get_source(self, source_id: int) -> RecipeSource:
        source = (
            self.db.query(RecipeSource)
            .options(
                joinedload(RecipeSource.extraction).joinedload(
                    RecipeSourceExtraction.ingredients
                ),
                joinedload(RecipeSource.extraction).joinedload(
                    RecipeSourceExtraction.steps
                ),
                joinedload(RecipeSource.extraction).joinedload(
                    RecipeSourceExtraction.labels
                ),
                joinedload(RecipeSource.extraction).joinedload(
                    RecipeSourceExtraction.quality_score
                ),
            )
            .filter(RecipeSource.source_id == source_id)
            .first()
        )
        if not source:
            raise RecipeSourceNotFoundError(source_id)
        return source

    def update_source(self, source_id: int, body: RecipeSourceUpdate) -> RecipeSource:
        source = self.get_source(source_id)

        if body.extraction is not None:
            source.extraction = _build_extraction(source.source_id, body.extraction)
            source.parse_status = "PARSED"
            source.parsed_at = datetime.now(UTC)

        if body.validation_errors is not None:
            source.validation_errors = body.validation_errors
        if body.parse_status is not None:
            source.parse_status = body.parse_status
        if body.review_status is not None:
            source.review_status = body.review_status

        self.db.commit()
        return self.get_source(source_id)

    def approve_source(self, source_id: int) -> RecipeSource:
        source = self.get_source(source_id)

        if source.import_status == "IMPORTED":
            raise RecipeSourceInvalidStatusError("이미 import된 source입니다.")

        errors = _validate_extraction(source.extraction)
        if errors:
            source.validation_errors = errors
            source.parse_status = "REVIEW_REQUIRED"
            source.review_status = "PENDING"
        else:
            source.validation_errors = []
            source.parse_status = "PARSED"
            source.review_status = "APPROVED"
            source.reviewed_at = datetime.now(UTC)

        self.db.commit()
        return self.get_source(source_id)

    def reject_source(self, source_id: int, reason: str) -> RecipeSource:
        source = self.get_source(source_id)

        if source.import_status == "IMPORTED":
            raise RecipeSourceInvalidStatusError(
                "이미 import된 source는 거절할 수 없습니다."
            )

        source.review_status = "REJECTED"
        source.reviewed_at = datetime.now(UTC)
        source.validation_errors = [{"code": "REJECTED", "message": reason}]

        self.db.commit()
        return self.get_source(source_id)


def _build_extraction(source_id: int, data) -> RecipeSourceExtraction:
    extraction = RecipeSourceExtraction(
        source_id=source_id,
        title=data.title,
        summary=data.summary,
        description=data.description,
        servings=data.servings,
        cooking_time_minutes=data.cooking_time_minutes,
        kcal_per_serving=data.kcal_per_serving,
        serving_weight_grams=data.serving_weight_grams,
        carbohydrate_grams=data.carbohydrate_grams,
        protein_grams=data.protein_grams,
        fat_grams=data.fat_grams,
        sodium_milligrams=data.sodium_milligrams,
        nutrition_source=data.nutrition_source,
        nutrition_raw=data.nutrition_raw,
        difficulty=data.difficulty,
        source_main_image_url=data.source_main_image_url,
        source_thumbnail_url=data.source_thumbnail_url,
        source_video_url=data.source_video_url,
        content_hash=data.content_hash,
    )
    if data.quality_score is not None:
        extraction.quality_score = RecipeSourceQualityScore(
            **data.quality_score.model_dump(exclude_none=True)
        )
    extraction.ingredients = [
        RecipeSourceExtractedIngredient(**item.model_dump(exclude_none=True))
        for item in data.ingredients
    ]
    extraction.steps = [
        RecipeSourceExtractedStep(**item.model_dump(exclude_none=True))
        for item in data.steps
    ]
    extraction.labels = [
        RecipeSourceExtractedLabel(**item.model_dump(exclude_none=True))
        for item in data.labels
    ]
    return extraction


def _validate_extraction(extraction: RecipeSourceExtraction | None) -> list[dict]:
    if extraction is None:
        return [
            {
                "code": "MISSING_EXTRACTION",
                "message": "파싱된 후보 데이터가 없습니다.",
            }
        ]

    errors = []
    if not extraction.title:
        errors.append({"code": "MISSING_TITLE", "message": "제목이 없습니다."})
    if not extraction.description and not extraction.summary:
        errors.append(
            {
                "code": "MISSING_DESCRIPTION",
                "message": "설명 또는 요약이 없습니다.",
            }
        )
    if not extraction.ingredients:
        errors.append({"code": "MISSING_INGREDIENTS", "message": "재료가 없습니다."})
    if not extraction.steps:
        errors.append({"code": "MISSING_STEPS", "message": "조리 단계가 없습니다."})
    if not extraction.servings:
        errors.append({"code": "MISSING_SERVINGS", "message": "인분 정보가 없습니다."})
    if not extraction.cooking_time_minutes:
        errors.append(
            {"code": "MISSING_COOKING_TIME", "message": "조리 시간이 없습니다."}
        )
    if extraction.difficulty not in VALID_DIFFICULTIES:
        errors.append(
            {
                "code": "INVALID_DIFFICULTY",
                "message": (
                    "난이도는 easy/normal/hard 중 하나여야 합니다: "
                    f"{extraction.difficulty}"
                ),
            }
        )
    if not any(label.label_type == "CATEGORY" for label in extraction.labels):
        errors.append({"code": "MISSING_CATEGORY", "message": "카테고리가 없습니다."})
    errors.extend(
        recipe_classification_service.validate_extraction_classification(extraction)
    )
    return errors
