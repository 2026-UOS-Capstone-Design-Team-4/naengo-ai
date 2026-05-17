"""
만개의레시피 recipe_source_extractions 초기화 스크립트.

extraction을 삭제하고 parse_status를 NOT_PARSED로 되돌린다.

Usage:
    uv run python scripts/reset_10000recipe_extractions.py
    uv run python scripts/reset_10000recipe_extractions.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe_source import RecipeSource, RecipeSourceExtraction
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_SITE = "10000recipe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        sources = (
            db.query(RecipeSource)
            .filter(RecipeSource.source_site == SOURCE_SITE)
            .all()
        )
        source_ids = [s.source_id for s in sources]
        logger.info("대상 source: %d개", len(sources))

        extraction_count = (
            db.query(RecipeSourceExtraction)
            .filter(RecipeSourceExtraction.source_id.in_(source_ids))
            .count()
        )
        logger.info("삭제할 extraction: %d개", extraction_count)

        if args.dry_run:
            logger.info("dry-run 모드 — 변경 없음")
            return

        deleted = (
            db.query(RecipeSourceExtraction)
            .filter(RecipeSourceExtraction.source_id.in_(source_ids))
            .delete(synchronize_session=False)
        )

        for source in sources:
            source.parse_status = "NOT_PARSED"
            source.review_status = "PENDING"
            source.import_status = "NOT_IMPORTED"
            source.validation_errors = None
            source.parsed_at = None
            source.raw_content_hash = None
            source.extraction_version = None

        db.commit()
        logger.info(
            "extraction %d개 삭제, source %d개 NOT_PARSED로 초기화 완료",
            deleted,
            len(sources),
        )


if __name__ == "__main__":
    main()
