"""
10000recipe PARSED 상태 recipe_sources를 일괄 APPROVED 처리하는 CLI.

Usage:
    uv run python scripts/ingestion/bulk_approve_10000recipe_sources.py --limit 300
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402,F401
from app.models.recipe_source import RecipeSource  # noqa: E402
from app.models.social import Like, Scrap  # noqa: E402,F401
from app.models.user import User, UserProfile  # noqa: E402,F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
SOURCE_SITE = "10000recipe"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="10000recipe PARSED sources APPROVED 처리"
    )
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(RecipeSource).filter(
            RecipeSource.source_site == SOURCE_SITE,
            RecipeSource.parse_status == "PARSED",
            RecipeSource.review_status == "PENDING",
            RecipeSource.import_status == "NOT_IMPORTED",
        )

        sources = query.limit(args.limit).all()
        logger.info("%s %d개 approve 대상", SOURCE_SITE, len(sources))

        now = datetime.now(UTC)
        for source in sources:
            source.review_status = "APPROVED"
            source.reviewed_at = now

        if not args.dry_run:
            db.commit()
            logger.info("완료: %s %d개 APPROVED", SOURCE_SITE, len(sources))
        else:
            db.rollback()
            logger.info("[dry-run] 커밋하지 않음")
    finally:
        db.close()


if __name__ == "__main__":
    main()


