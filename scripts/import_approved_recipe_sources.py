"""
APPROVED 상태 recipe_sources를 recipes 테이블로 import하는 CLI.

Usage:
    uv run python scripts/import_approved_recipe_sources.py --limit 200
    uv run python scripts/import_approved_recipe_sources.py --limit 200 --workers 4
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.recipe_source import RecipeSource
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.ingestion.recipe_import_service import RecipeImportService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def import_one(source_id: int) -> tuple[str, int, int | None]:
    with SessionLocal() as db:
        service = RecipeImportService(db)
        try:
            recipe = service.import_source(source_id)
            logger.info(
                "[IMPORTED] source_id=%d -> recipe_id=%d",
                source_id,
                recipe.recipe_id,
            )
            return "IMPORTED", source_id, recipe.recipe_id
        except Exception as exc:
            logger.error("[FAILED] source_id=%d: %s", source_id, exc)
            return "FAILED", source_id, None


def main() -> None:
    parser = argparse.ArgumentParser(description="recipe_sources -> recipes import")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="동시에 import할 source 수입니다. 기본값 1은 기존처럼 순차 실행합니다.",
    )
    args = parser.parse_args()
    workers = max(1, args.workers)

    # source ID 목록만 먼저 조회하고, source마다 새 세션으로 import한다.
    # 같은 세션을 재사용하면 rollback 뒤 identity map에 오류 객체가 남아
    # 다음 source 처리에서 PK 충돌이 일어나는 문제를 막기 위함이다.
    with SessionLocal() as db:
        source_ids = [
            row[0]
            for row in db.query(RecipeSource.source_id)
            .filter(
                RecipeSource.review_status == "APPROVED",
                RecipeSource.import_status == "NOT_IMPORTED",
            )
            .limit(args.limit)
            .all()
        ]

    logger.info("%d개 import 시작 (workers=%d)", len(source_ids), workers)

    counts: dict[str, int] = {}
    if workers == 1:
        for source_id in source_ids:
            status, _, _ = import_one(source_id)
            counts[status] = counts.get(status, 0) + 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(import_one, source_id) for source_id in source_ids
            ]
            for future in as_completed(futures):
                status, _, _ = future.result()
                counts[status] = counts.get(status, 0) + 1

    logger.info("완료: %s", counts)


if __name__ == "__main__":
    main()
