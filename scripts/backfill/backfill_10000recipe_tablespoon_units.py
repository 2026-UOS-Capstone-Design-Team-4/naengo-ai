"""
10000recipe staging ingredients의 숟가락 계열 단위를 T로 백필합니다.

Usage:
    uv run python scripts/backfill/backfill_10000recipe_tablespoon_units.py --dry-run
    uv run python scripts/backfill/backfill_10000recipe_tablespoon_units.py
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402,F401
from app.models.recipe import Recipe  # noqa: E402,F401
from app.models.recipe_source import (  # noqa: E402
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtraction,
)
from app.models.social import Like, Scrap  # noqa: E402,F401
from app.models.user import User, UserProfile  # noqa: E402,F401
from scripts.ingestion.parse_10000recipe_sources import (  # noqa: E402
    _normalize_amount_text,
    _parse_amount,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_SITE = "10000recipe"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="10000recipe 숟가락 계열 단위 T 백필"
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = (
            db.query(RecipeSourceExtractedIngredient)
            .join(RecipeSourceExtraction)
            .join(RecipeSource)
            .options(joinedload(RecipeSourceExtractedIngredient.extraction))
            .filter(
                RecipeSource.source_site == SOURCE_SITE,
                or_(
                    RecipeSourceExtractedIngredient.amount_text.contains("숟"),
                    RecipeSourceExtractedIngredient.unit.in_(
                        ("밥숟가락", "밥 숟가락", "숟가락", "숟갈")
                    ),
                ),
            )
            .order_by(RecipeSourceExtractedIngredient.extracted_ingredient_id)
        )
        if args.limit:
            query = query.limit(args.limit)

        ingredients = query.all()
        scanned_count = len(ingredients)
        updated_count = 0

        for ingredient in ingredients:
            if _normalize_ingredient(ingredient):
                updated_count += 1
                logger.info(
                    "[UPDATED] extracted_ingredient_id=%d amount_text=%s unit=%s",
                    ingredient.extracted_ingredient_id,
                    ingredient.amount_text,
                    ingredient.unit,
                )

        if args.dry_run:
            db.rollback()
            logger.info(
                "[dry-run] scanned=%d updated=%d 커밋하지 않음",
                scanned_count,
                updated_count,
            )
        else:
            db.commit()
            logger.info("완료: scanned=%d updated=%d", scanned_count, updated_count)
    finally:
        db.close()


def _normalize_ingredient(ingredient: RecipeSourceExtractedIngredient) -> bool:
    old_amount_text = ingredient.amount_text
    new_amount_text = _normalize_amount_text(old_amount_text)
    quantity, unit = _parse_amount(new_amount_text)

    changed = (
        new_amount_text != old_amount_text
        or quantity != ingredient.quantity
        or unit != ingredient.unit
    )
    if not changed:
        return False

    old_generated_raw_text = (
        f"{ingredient.name} {old_amount_text}".strip()
        if old_amount_text
        else ingredient.name
    )
    new_generated_raw_text = (
        f"{ingredient.name} {new_amount_text}".strip()
        if new_amount_text
        else ingredient.name
    )

    ingredient.amount_text = new_amount_text
    ingredient.quantity = quantity
    ingredient.unit = unit
    if ingredient.raw_text == old_generated_raw_text:
        ingredient.raw_text = new_generated_raw_text
    return True


if __name__ == "__main__":
    main()
