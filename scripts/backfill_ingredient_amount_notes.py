"""
Move parenthesized amount hints from amount_text to note.

Usage:
    uv run python scripts/backfill_ingredient_amount_notes.py
    uv run python scripts/backfill_ingredient_amount_notes.py --dry-run
"""

# ruff: noqa: I001

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.recipe_source import RecipeSourceExtractedIngredient
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.ingestion.ingredient_amount_note_service import (
    move_amount_parentheses_to_note,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _has_parentheses(value: str | None) -> bool:
    return bool(value and any(char in value for char in "()（）"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    updated = 0
    with SessionLocal() as db:
        rows = (
            db.query(RecipeSourceExtractedIngredient)
            .filter(RecipeSourceExtractedIngredient.amount_text.isnot(None))
            .all()
        )
        for row in rows:
            if not _has_parentheses(row.amount_text):
                continue
            split = move_amount_parentheses_to_note(row.amount_text, row.note)
            if split.amount_text == row.amount_text and split.note == row.note:
                continue
            logger.info(
                "ingredient_id=%d %s: amount=%r -> %r, note=%r -> %r",
                row.extracted_ingredient_id,
                row.name,
                row.amount_text,
                split.amount_text,
                row.note,
                split.note,
            )
            if not args.dry_run:
                row.amount_text = split.amount_text
                row.note = split.note
            updated += 1
        if not args.dry_run:
            db.commit()
    logger.info("done: updated=%d dry_run=%s", updated, args.dry_run)


if __name__ == "__main__":
    main()
