import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.models.recipe import (
    Recipe,
    RecipeIngredient,
    RecipeLabel,
    RecipeNutrition,
    RecipeQualityScore,
    RecipeStep,
)
from app.models.recipe_source import RecipeSource, RecipeSourceExtraction
from app.services.ingestion.recipe_source_service import (
    RecipeSourceInvalidStatusError,
    RecipeSourceNotFoundError,
)
from app.services.ingestion.recipe_text_rewrite_service import (
    RecipeTextDraft,
    RecipeTextRewriter,
    draft_from_extraction,
    recipe_text_rewrite_service,
)
from app.services.recipe_embedding_service import (
    RecipeSearchEmbeddingIngredient,
    RecipeSearchEmbeddingInput,
    recipe_embedding_service,
)
from app.services.storage_service import StorageService, storage_service

logger = logging.getLogger(__name__)


class RecipeImportService:
    def __init__(
        self,
        db: Session,
        storage: StorageService = storage_service,
        text_rewriter: RecipeTextRewriter = recipe_text_rewrite_service,
    ):
        self.db = db
        self.storage = storage
        self.text_rewriter = text_rewriter

    def import_source(self, source_id: int) -> Recipe:
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
        if source.review_status != "APPROVED":
            raise RecipeSourceInvalidStatusError(
                f"APPROVED source만 import할 수 있습니다. 현재: {source.review_status}"
            )
        if source.import_status == "IMPORTED":
            raise RecipeSourceInvalidStatusError("이미 import된 source입니다.")
        if source.extraction is None:
            raise RecipeSourceInvalidStatusError("파싱된 extraction이 없습니다.")

        try:
            import_draft = self._build_import_draft(source)
            recipe = self._create_recipe(source, import_draft)
            self.db.add(recipe)
            self.db.flush()

            self._add_ingredients(recipe.recipe_id, import_draft)
            self._add_steps(recipe.recipe_id, import_draft)
            self._add_labels(recipe.recipe_id, source.extraction.labels)
            self._add_nutrition(recipe.recipe_id, source.extraction)
            self._add_quality_score(recipe.recipe_id, source.extraction)
            self._add_embedding(recipe.recipe_id, import_draft, source.extraction)

            source.import_status = "IMPORTED"
            source.imported_recipe_id = recipe.recipe_id
            source.imported_at = datetime.now(UTC)

            self.db.commit()
            self.db.refresh(recipe)
            logger.info(
                "import 완료: source_id=%d, recipe_id=%d",
                source_id,
                recipe.recipe_id,
            )
            return recipe
        except Exception:
            self.db.rollback()
            source.import_status = "FAILED"
            self.db.commit()
            raise

    def _build_import_draft(self, source: RecipeSource) -> RecipeTextDraft:
        if source.extraction_version in (
            "foodsafetykorea-extraction-v1",
            "10000recipe-extraction-v1",
        ):
            return draft_from_extraction(source.extraction)
        return self.text_rewriter.rewrite(source.extraction)

    def _create_recipe(self, source: RecipeSource, draft: RecipeTextDraft) -> Recipe:
        extraction = source.extraction
        return Recipe(
            source_id=source.source_id,
            title=draft.title,
            summary=draft.summary,
            description=draft.description,
            servings=float(extraction.servings or 1),
            cooking_time_minutes=int(extraction.cooking_time_minutes or 0),
            kcal_per_serving=extraction.kcal_per_serving,
            difficulty=extraction.difficulty or "normal",
            visibility="PUBLIC",
            author_type="SOURCE",
            is_active=True,
        )

    def _add_ingredients(self, recipe_id: int, draft: RecipeTextDraft) -> None:
        for ingredient in draft.ingredients:
            self.db.add(
                RecipeIngredient(
                    recipe_id=recipe_id,
                    group_name=ingredient.group_name,
                    name=ingredient.name,
                    normalized_name=ingredient.normalized_name or ingredient.name,
                    amount_text=ingredient.amount_text,
                    quantity=ingredient.quantity,
                    unit=ingredient.unit,
                    note=ingredient.note,
                    raw_text=ingredient.raw_text,
                    is_optional=ingredient.is_optional,
                    sort_order=ingredient.sort_order,
                )
            )

    def _add_steps(self, recipe_id: int, draft: RecipeTextDraft) -> None:
        for step in draft.steps:
            recipe_step = RecipeStep(
                recipe_id=recipe_id,
                step_no=step.step_no,
                instruction=step.instruction,
                tip=step.tip,
                sort_order=step.sort_order,
            )
            self.db.add(recipe_step)

    def _add_labels(self, recipe_id: int, labels: list) -> None:
        for label in labels:
            self.db.add(
                RecipeLabel(
                    recipe_id=recipe_id,
                    label_type=label.label_type,
                    label_value=label.label_value,
                    source=label.source,
                    confidence_score=label.confidence_score,
                    sort_order=label.sort_order,
                )
            )

    def _add_nutrition(
        self,
        recipe_id: int,
        extraction: RecipeSourceExtraction,
    ) -> None:
        has_nutrition = any(
            value is not None
            for value in [
                extraction.serving_weight_grams,
                extraction.kcal_per_serving,
                extraction.carbohydrate_grams,
                extraction.protein_grams,
                extraction.fat_grams,
                extraction.sodium_milligrams,
            ]
        )
        if not has_nutrition:
            return

        self.db.add(
            RecipeNutrition(
                recipe_id=recipe_id,
                serving_weight_grams=extraction.serving_weight_grams,
                kcal_per_serving=extraction.kcal_per_serving,
                carbohydrate_grams=extraction.carbohydrate_grams,
                protein_grams=extraction.protein_grams,
                fat_grams=extraction.fat_grams,
                sodium_milligrams=extraction.sodium_milligrams,
                source=extraction.nutrition_source or "SOURCE",
                raw_payload=extraction.nutrition_raw or {},
            )
        )

    def _add_quality_score(
        self,
        recipe_id: int,
        extraction: RecipeSourceExtraction,
    ) -> None:
        source_quality = extraction.quality_score
        if source_quality is None:
            return

        self.db.merge(
            RecipeQualityScore(
                recipe_id=recipe_id,
                completeness_score=source_quality.completeness_score,
                nutrition_confidence=source_quality.nutrition_confidence,
                duplicate_score=source_quality.duplicate_score,
                reviewed_by=source_quality.reviewed_by,
                reviewed_at=source_quality.reviewed_at,
            )
        )

    def _add_embedding(
        self,
        recipe_id: int,
        draft: RecipeTextDraft,
        extraction: RecipeSourceExtraction,
    ) -> None:
        data = RecipeSearchEmbeddingInput(
            title=draft.title,
            summary=draft.summary,
            description=draft.description,
            ingredients=[
                RecipeSearchEmbeddingIngredient(
                    name=item.name,
                    normalized_name=item.normalized_name,
                    amount_text=item.amount_text,
                )
                for item in draft.ingredients
            ],
            categories=_label_values(extraction, "CATEGORY"),
            tips=draft.tips,
            cooking_time_minutes=int(extraction.cooking_time_minutes)
            if extraction.cooking_time_minutes
            else None,
            difficulty=extraction.difficulty,
            kcal_per_serving=(
                int(extraction.kcal_per_serving)
                if extraction.kcal_per_serving
                else None
            ),
        )
        self.db.add(
            recipe_embedding_service.create_search_embedding(
                recipe_id=recipe_id,
                data=data,
            )
        )


def _label_values(
    extraction: RecipeSourceExtraction,
    label_type: str,
) -> list[str]:
    return [
        label.label_value
        for label in extraction.labels
        if label.label_type == label_type and label.label_value
    ]
