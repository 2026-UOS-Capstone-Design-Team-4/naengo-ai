"""
Backfill recipe_source_extractions.cooking_time_minutes with AI estimates.

Usage:
    uv run python scripts/backfill_source_cooking_time.py --threshold 40
    uv run python scripts/backfill_source_cooking_time.py --threshold 40 --dry-run
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
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import API_KEY, BASE_URL, MODEL_NAME
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.recipe_source import RecipeSourceExtraction
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 20
MAX_COOKING_TIME_MINUTES = 120

_SYSTEM_PROMPT = """
You estimate a recipe's total cooking time in minutes.

Return only the structured output:
- cooking_time_minutes: practical app-facing cooking minutes from ingredient prep
  through serving.

Rules:
- Use explicit recipe time when it is credible.
- If source time looks like a bad unit conversion, ignore it and estimate from steps.
- Include washing, cutting, boiling, baking, simmering, and ordinary short rests.
- Do not count long passive waits at full length. Overnight salting, multi-hour
  steeping, marinating, freezing, chilling, or storage should be treated as advance
  prep and excluded from the app-facing cooking time.
- For recipes with long passive waits, estimate the active handling plus active
  heating/cooking time needed in one cooking session.
- If the practical app-facing cooking time is over 120 minutes, return null.
- Return a positive integer. Use null only when there is too little evidence.
""".strip()


class CookingTimeOutput(BaseModel):
    cooking_time_minutes: int | None = None


_agent: Agent | None = None


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        model = OpenAIChatModel(
            MODEL_NAME,
            provider=OpenAIProvider(api_key=API_KEY, base_url=BASE_URL),
        )
        _agent = Agent(
            model,
            output_type=CookingTimeOutput,
            system_prompt=_SYSTEM_PROMPT,
        )
    return _agent


def _payload(extraction: RecipeSourceExtraction) -> dict[str, Any]:
    source = extraction.source
    raw_payload = source.raw_payload if source is not None else {}
    return {
        "source_site": source.source_site if source is not None else None,
        "current_cooking_time_minutes": extraction.cooking_time_minutes,
        "title": extraction.title,
        "summary": extraction.summary,
        "description": extraction.description,
        "servings": float(extraction.servings) if extraction.servings else None,
        "source_time_text": _source_time_text(raw_payload),
        "ingredients": [
            {
                "name": item.name,
                "amount_text": item.amount_text,
                "raw_text": item.raw_text,
            }
            for item in extraction.ingredients[:30]
        ],
        "steps": [
            {
                "step_no": item.step_no,
                "instruction": item.instruction,
                "raw_text": item.raw_text,
            }
            for item in extraction.steps[:20]
        ],
        "raw_payload_hint": _raw_payload_hint(raw_payload),
    }


def _source_time_text(raw_payload: Any) -> Any:
    if not isinstance(raw_payload, dict):
        return None
    return (
        raw_payload.get("cooking_time_raw")
        or raw_payload.get("time")
        or raw_payload.get("cook_time")
        or raw_payload.get("cooking_time")
    )


def _raw_payload_hint(raw_payload: Any) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        return {}
    keys = [
        "name",
        "title",
        "method",
        "category",
        "description",
        "manual_steps",
        "instructions",
    ]
    return {key: raw_payload.get(key) for key in keys if raw_payload.get(key)}


def estimate_cooking_time(extraction: RecipeSourceExtraction) -> int | None:
    try:
        result = _get_agent().run_sync(
            json.dumps(_payload(extraction), ensure_ascii=False, indent=2)
        )
    except Exception as exc:
        logger.warning(
            "cooking time estimate failed (extraction_id=%d): %s",
            extraction.extraction_id,
            exc,
        )
        return None
    value = result.output.cooking_time_minutes
    if not value or value <= 0:
        return None
    if value > MAX_COOKING_TIME_MINUTES:
        return None
    return value


def _fetch_candidates(db, threshold: int, limit: int | None) -> list[int]:
    query = (
        db.query(RecipeSourceExtraction.extraction_id)
        .filter(RecipeSourceExtraction.cooking_time_minutes > threshold)
        .order_by(RecipeSourceExtraction.cooking_time_minutes.desc())
    )
    if limit:
        query = query.limit(limit)
    return [row[0] for row in query.all()]


def _fetch_extraction(db, extraction_id: int) -> RecipeSourceExtraction | None:
    return (
        db.query(RecipeSourceExtraction)
        .options(
            joinedload(RecipeSourceExtraction.source),
            joinedload(RecipeSourceExtraction.ingredients),
            joinedload(RecipeSourceExtraction.steps),
        )
        .filter(RecipeSourceExtraction.extraction_id == extraction_id)
        .first()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=40)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        extraction_ids = _fetch_candidates(db, args.threshold, args.limit)

    logger.info(
        "candidates: %d rows over %d minutes",
        len(extraction_ids),
        args.threshold,
    )

    updated = 0
    skipped = 0
    failed = 0

    for index, extraction_id in enumerate(extraction_ids, start=1):
        with SessionLocal() as db:
            extraction = _fetch_extraction(db, extraction_id)
            if extraction is None:
                skipped += 1
                continue

            before = extraction.cooking_time_minutes
            after = estimate_cooking_time(extraction)
            if after is None:
                logger.info(
                    "[%d/%d] extraction_id=%d %s: %s -> null",
                    index,
                    len(extraction_ids),
                    extraction_id,
                    extraction.title,
                    before,
                )
                if not args.dry_run:
                    extraction.cooking_time_minutes = None
                    db.commit()
                updated += 1
                continue

            logger.info(
                "[%d/%d] extraction_id=%d %s: %s -> %s",
                index,
                len(extraction_ids),
                extraction_id,
                extraction.title,
                before,
                after,
            )
            if not args.dry_run:
                extraction.cooking_time_minutes = after
                db.commit()
            updated += 1

    logger.info(
        "done: updated=%d skipped=%d failed=%d dry_run=%s",
        updated,
        skipped,
        failed,
        args.dry_run,
    )


if __name__ == "__main__":
    main()
