"""
기존 recipes에 recipe_classifications를 백필하는 CLI.

Usage:
    uv run python scripts/backfill_recipe_classifications.py --limit 500
    uv run python scripts/backfill_recipe_classifications.py --limit 500 --refresh
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import (
    Recipe,
    RecipeQualityScore,
)
from app.models.recipe_source import RecipeSource  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.ingestion.recipe_classification_service import (
    ClassificationBuildResult,
    recipe_classification_service,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="recipe_classifications 백필")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="기존 classification도 다시 계산해 덮어씁니다.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = (
            db.query(Recipe)
            .options(
                selectinload(Recipe.ingredients_list),
                selectinload(Recipe.steps),
                selectinload(Recipe.labels),
                selectinload(Recipe.classifications),
            )
            .filter(Recipe.is_active.is_(True))
            .order_by(Recipe.recipe_id)
        )
        if not args.refresh:
            query = query.filter(
                Recipe.classification_status.in_(("NOT_CLASSIFIED", "FAILED"))
            )

        recipes = query.limit(args.limit).all()
        logger.info("%d개 recipe classification 백필 시작", len(recipes))

        counts = {"UPDATED": 0, "REVIEW_REQUIRED": 0, "FAILED": 0}
        for recipe in recipes:
            recipe_id = recipe.recipe_id
            try:
                result = recipe_classification_service.build_from_recipe(recipe)
                _save_result(db, result)
                if result.review_required:
                    recipe.classification_status = "REVIEW_REQUIRED"
                    recipe.classified_at = datetime.now(UTC)
                    db.commit()
                    counts["REVIEW_REQUIRED"] += 1
                    logger.info(
                        "[REVIEW_REQUIRED] recipe_id=%d reasons=%s",
                        recipe.recipe_id,
                        result.review_reasons,
                    )
                else:
                    recipe.classification_status = "CLASSIFIED"
                    recipe.classified_at = datetime.now(UTC)
                    db.commit()
                    counts["UPDATED"] += 1
                    logger.info(
                        "[UPDATED] recipe_id=%d confidence=%s",
                        recipe.recipe_id,
                        result.classification.confidence_score,
                    )
            except Exception as exc:
                db.rollback()
                failed_recipe = db.get(Recipe, recipe_id)
                if failed_recipe is not None:
                    failed_recipe.classification_status = "FAILED"
                    failed_recipe.classified_at = datetime.now(UTC)
                    db.commit()
                counts["FAILED"] += 1
                logger.error("[FAILED] recipe_id=%d: %s", recipe_id, exc)

        db.commit()
        logger.info("완료: %s", counts)
    finally:
        db.close()


def _save_result(db, result: ClassificationBuildResult) -> None:
    db.merge(result.classification)

    quality = db.get(RecipeQualityScore, result.quality_score.recipe_id)
    if quality is None:
        db.add(result.quality_score)
    else:
        quality.classification_confidence = (
            result.quality_score.classification_confidence
        )

    db.flush()


if __name__ == "__main__":
    main()
