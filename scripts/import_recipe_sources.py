"""
APPROVED 상태 recipe_sources를 recipes 테이블로 import하는 CLI.

Usage:
    uv run python scripts/import_recipe_sources.py --limit 200
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe_source import RecipeSource
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.recipe_import_service import RecipeImportService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="recipe_sources → recipes import")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    service = RecipeImportService(db)
    try:
        sources = (
            db.query(RecipeSource)
            .filter(
                RecipeSource.review_status == "APPROVED",
                RecipeSource.import_status == "NOT_IMPORTED",
            )
            .limit(args.limit)
            .all()
        )
        logger.info("%d개 import 시작", len(sources))

        counts: dict[str, int] = {}
        for source in sources:
            try:
                recipe = service.import_source(source.source_id)
                counts["IMPORTED"] = counts.get("IMPORTED", 0) + 1
                logger.info("[IMPORTED] source_id=%d → recipe_id=%d", source.source_id, recipe.recipe_id)
            except Exception as exc:
                counts["FAILED"] = counts.get("FAILED", 0) + 1
                logger.error("[FAILED] source_id=%d: %s", source.source_id, exc)

        logger.info("완료: %s", counts)
    finally:
        db.close()


if __name__ == "__main__":
    main()
