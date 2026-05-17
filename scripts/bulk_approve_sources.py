"""
PARSED 상태 recipe_sources를 일괄 APPROVED 처리하는 CLI.

신뢰할 수 있는 소스(공공데이터 등)를 관리자 검수 없이 bulk approve할 때 사용.

Usage:
    uv run python scripts/bulk_approve_sources.py --dataset-id foodsafetykorea-recipe
    uv run python scripts/bulk_approve_sources.py  # 전체 PARSED 대상
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402,F401
from app.models.recipe_source import RecipeSource  # noqa: E402
from app.models.social import Like, Scrap  # noqa: E402,F401
from app.models.user import User, UserProfile  # noqa: E402,F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="PARSED sources 일괄 APPROVED 처리")
    parser.add_argument("--dataset-id", help="특정 dataset_id만 처리 (미지정시 전체)")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(RecipeSource).filter(
            RecipeSource.parse_status == "PARSED",
            RecipeSource.review_status == "PENDING",
            RecipeSource.import_status == "NOT_IMPORTED",
        )
        if args.dataset_id:
            query = query.filter(RecipeSource.source_dataset_id == args.dataset_id)

        sources = query.limit(args.limit).all()
        logger.info("%d개 approve 대상", len(sources))

        now = datetime.now(UTC)
        for source in sources:
            source.review_status = "APPROVED"
            source.reviewed_at = now

        if not args.dry_run:
            db.commit()
            logger.info("완료: %d개 APPROVED", len(sources))
        else:
            db.rollback()
            logger.info("[dry-run] 커밋하지 않음")
    finally:
        db.close()


if __name__ == "__main__":
    main()
