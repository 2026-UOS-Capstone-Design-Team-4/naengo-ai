"""
foodsafetykorea extraction의 kcal_per_serving 필드를 backfill합니다.

Usage:
    uv run python scripts/backfill_foodsafetykorea_kcal_per_serving.py --limit 100
    uv run python scripts/backfill_foodsafetykorea_kcal_per_serving.py --dry-run
"""

# ruff: noqa: I001

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import joinedload

from app.core.config import API_KEY, BASE_URL, MODEL_NAME
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.models.recipe_source import RecipeSource, RecipeSourceExtraction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_SITE = "foodsafetykorea"

_SYSTEM_PROMPT = """
You estimate per-serving kilocalories for a recipe given its nutrition data and
serving count.

Return only the structured output:
- kcal_per_serving: estimated kilocalories per single serving as an integer.
  Use null only when there is genuinely insufficient information to make any estimate.

Rules:
- If raw_nutrition.calories is present, divide it by servings to get per-serving
  kcal_per_serving (round to nearest integer).
- If raw_nutrition.calories is absent or null, estimate per-serving kcal from the
  ingredient list, quantities, and dish type using nutritional knowledge.
- Use other nutrition values (carbohydrate_g, protein_g, fat_g) to cross-check:
  kcal ≈ carbs_g * 4 + protein_g * 4 + fat_g * 9.
- Use null only when there is genuinely no basis for estimation.
""".strip()


class KcalOutput(BaseModel):
    kcal_per_serving: int | None = None


_agent: Agent | None = None


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        model = OpenAIChatModel(
            MODEL_NAME,
            provider=OpenAIProvider(api_key=API_KEY, base_url=BASE_URL),
        )
        _agent = Agent(model, output_type=KcalOutput, system_prompt=_SYSTEM_PROMPT)
    return _agent


def _build_prompt(
    title: str,
    servings: float | None,
    nutrition_raw: dict[str, Any],
    ingredient_names: list[str],
) -> str:
    payload = {
        "title": title,
        "servings": servings,
        "raw_nutrition": {
            "calories": nutrition_raw.get("calories"),
            "carbohydrate_g": nutrition_raw.get("carbohydrate"),
            "protein_g": nutrition_raw.get("protein"),
            "fat_g": nutrition_raw.get("fat"),
            "sodium_mg": nutrition_raw.get("sodium"),
        },
        "ingredient_names": ingredient_names[:20],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def estimate_kcal_per_serving(
    title: str,
    servings: float | None,
    nutrition_raw: dict[str, Any],
    ingredient_names: list[str],
) -> int | None:
    try:
        result = _get_agent().run_sync(
            _build_prompt(title, servings, nutrition_raw, ingredient_names)
        )
        return result.output.kcal_per_serving
    except Exception as exc:
        logger.warning("칼로리 추정 실패 (%s): %s", title, exc)
        return None


BATCH_SIZE = 50


def _fetch_batch(db, offset: int, limit: int) -> list:
    return (
        db.query(RecipeSourceExtraction)
        .join(RecipeSource, RecipeSource.source_id == RecipeSourceExtraction.source_id)
        .filter(RecipeSource.source_site == SOURCE_SITE)
        .options(joinedload(RecipeSourceExtraction.ingredients))
        .order_by(RecipeSourceExtraction.extraction_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 건수")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB에 저장하지 않고 결과만 출력",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        total = (
            db.query(RecipeSourceExtraction)
            .join(
                RecipeSource,
                RecipeSource.source_id == RecipeSourceExtraction.source_id,
            )
            .filter(RecipeSource.source_site == SOURCE_SITE)
            .count()
        )
        max_count = min(args.limit, total) if args.limit else total
        logger.info("backfill 대상: %d건 (총 %d건)", max_count, total)
    finally:
        db.close()

    updated = 0
    failed = 0
    processed = 0
    offset = 0

    while processed < max_count:
        batch_size = min(BATCH_SIZE, max_count - processed)
        db = SessionLocal()
        try:
            extractions = _fetch_batch(db, offset, batch_size)
            if not extractions:
                break

            rows = [
                (
                    e.extraction_id,
                    e.title or "",
                    float(e.servings) if e.servings else None,
                    e.nutrition_raw or {},
                    [ing.name for ing in e.ingredients if ing.name],
                )
                for e in extractions
            ]
        finally:
            db.close()

        for extraction_id, title, servings, nutrition_raw, ingredient_names in rows:
            kcal_per_serving = estimate_kcal_per_serving(
                title,
                servings,
                nutrition_raw,
                ingredient_names,
            )

            if kcal_per_serving is None:
                logger.warning(
                    "칼로리 추정 불가: %s (extraction_id=%d)",
                    title,
                    extraction_id,
                )
                failed += 1
            else:
                logger.info(
                    "칼로리 추정: %s → %d kcal/serving (extraction_id=%d)",
                    title,
                    kcal_per_serving,
                    extraction_id,
                )
                if not args.dry_run:
                    db2 = SessionLocal()
                    try:
                        db2.query(RecipeSourceExtraction).filter(
                            RecipeSourceExtraction.extraction_id == extraction_id
                        ).update({"kcal_per_serving": kcal_per_serving})
                        db2.commit()
                        updated += 1
                    finally:
                        db2.close()
                else:
                    updated += 1

            processed += 1

        offset += len(rows)
        logger.info("진행: %d/%d건", processed, max_count)

    if not args.dry_run:
        logger.info("완료: %d건 업데이트, %d건 실패", updated, failed)
    else:
        logger.info("[dry-run] %d건 처리됨, DB 저장 없음", updated + failed)


if __name__ == "__main__":
    main()
