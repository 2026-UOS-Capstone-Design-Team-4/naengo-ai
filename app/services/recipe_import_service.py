import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.core.config import EMBEDDING_MODEL
from app.models.recipe import (
    Recipe,
    RecipeEmbedding,
    RecipeIngredient,
    RecipeLabel,
    RecipeMedia,
    RecipeStep,
)
from app.models.recipe_source import RecipeSource, RecipeSourceExtraction
from app.services.embedding_service import embedding_service
from app.services.recipe_source_service import (
    RecipeSourceInvalidStatusError,
    RecipeSourceNotFoundError,
)

logger = logging.getLogger(__name__)


class RecipeImportService:
    def __init__(self, db: Session):
        self.db = db

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
            recipe = self._create_recipe(source)
            self.db.add(recipe)
            self.db.flush()

            self._add_ingredients(recipe.recipe_id, source.extraction.ingredients)
            self._add_steps(recipe.recipe_id, source.extraction.steps)
            self._add_labels(recipe.recipe_id, source.extraction.labels)
            self._add_media(recipe.recipe_id, source.extraction)
            self._add_embedding(recipe.recipe_id, source.extraction)

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

    def _create_recipe(self, source: RecipeSource) -> Recipe:
        extraction = source.extraction
        return Recipe(
            source_id=source.source_id,
            title=extraction.title,
            subtitle=extraction.subtitle,
            summary=extraction.summary,
            description=(
                extraction.description
                or extraction.summary
                or extraction.title
            ),
            servings=float(extraction.servings or 1),
            prep_time_minutes=extraction.prep_time_minutes,
            cook_time_minutes=extraction.cook_time_minutes,
            total_time_minutes=int(extraction.total_time_minutes or 0),
            calories=extraction.calories,
            difficulty=extraction.difficulty or "normal",
            difficulty_score=extraction.difficulty_score,
            status="PUBLISHED",
            visibility="PUBLIC",
            author_type="SOURCE",
            source_author_name=source.source_author_name,
            source_author_url=source.source_author_url,
            source_url=source.source_url,
            source_site=source.source_site,
            source_recipe_id=source.source_recipe_id,
            source_published_at=source.source_published_at,
            is_active=True,
        )

    def _add_ingredients(self, recipe_id: int, ingredients: list) -> None:
        for ingredient in ingredients:
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

    def _add_steps(self, recipe_id: int, steps: list) -> None:
        for step in steps:
            recipe_step = RecipeStep(
                recipe_id=recipe_id,
                step_no=step.step_no,
                title=step.title,
                instruction=step.instruction,
                duration_minutes=step.duration_minutes,
                temperature=step.temperature,
                equipment=step.equipment,
                tip=step.tip,
                sort_order=step.sort_order,
            )
            self.db.add(recipe_step)
            self.db.flush()
            if step.source_image_url:
                self.db.add(
                    RecipeMedia(
                        recipe_id=recipe_id,
                        step_id=recipe_step.step_id,
                        media_type="IMAGE",
                        image_role="STEP",
                        source_url=step.source_image_url,
                        storage_url=step.source_image_url,
                        sort_order=step.sort_order,
                    )
                )

    def _add_labels(self, recipe_id: int, labels: list) -> None:
        for label in labels:
            self.db.add(
                RecipeLabel(
                    recipe_id=recipe_id,
                    label_type=label.label_type,
                    label_value=label.label_value,
                    normalized_value=label.label_value[:100],
                    source=label.source,
                    confidence_score=label.confidence_score,
                    sort_order=label.sort_order,
                )
            )

    def _add_media(self, recipe_id: int, extraction: RecipeSourceExtraction) -> None:
        if extraction.source_main_image_url:
            self.db.add(
                RecipeMedia(
                    recipe_id=recipe_id,
                    media_type="IMAGE",
                    image_role="MAIN",
                    source_url=extraction.source_main_image_url,
                    storage_url=extraction.source_main_image_url,
                    thumbnail_url=extraction.source_thumbnail_url,
                    is_primary=True,
                    sort_order=0,
                )
            )
        if extraction.source_video_url:
            self.db.add(
                RecipeMedia(
                    recipe_id=recipe_id,
                    media_type="VIDEO",
                    source_url=extraction.source_video_url,
                    storage_url=extraction.source_video_url,
                    sort_order=0,
                )
            )

    def _add_embedding(
        self,
        recipe_id: int,
        extraction: RecipeSourceExtraction,
    ) -> None:
        embedding_text = _build_embedding_text(extraction)
        try:
            vector = embedding_service.embed_query(embedding_text)
        except Exception as exc:
            logger.error("embedding 생성 실패: %s", exc)
            return

        self.db.add(
            RecipeEmbedding(
                recipe_id=recipe_id,
                embedding_type="RECIPE_SEARCH",
                model=EMBEDDING_MODEL,
                content_hash=hashlib.sha256(embedding_text.encode()).hexdigest(),
                embedding=vector,
            )
        )


def _build_embedding_text(extraction: RecipeSourceExtraction) -> str:
    ingredients = " ".join(item.name for item in extraction.ingredients)
    labels = " ".join(item.label_value for item in extraction.labels)
    steps = " ".join(item.instruction for item in extraction.steps[:5])
    return " ".join(
        part
        for part in [
            extraction.title,
            extraction.summary,
            extraction.description,
            ingredients,
            labels,
            steps,
            extraction.difficulty,
        ]
        if part
    )
