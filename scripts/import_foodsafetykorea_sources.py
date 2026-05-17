"""
공공데이터 foodsafetykorea 레시피 원본 JSON을 recipe_sources 테이블에 적재합니다.

Usage:
    uv run python scripts/import_foodsafetykorea_sources.py ^
      --input ..\\open-recipe\\data\\recipes.envcheck.json

recipe_source_extractions 생성은
scripts/parse_foodsafetykorea_sources.py에서 별도로 수행합니다.
"""

# ruff: noqa: I001

import argparse
import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402,F401
from app.models.social import Like, Scrap  # noqa: E402,F401
from app.models.user import User, UserProfile  # noqa: E402,F401
from app.models.recipe_source import RecipeSource  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SOURCE_SITE = "foodsafetykorea"
SOURCE_TYPE = "PUBLIC_DATA"
PARSER_TYPE = "DATASET"
DATASET_ID = "foodsafetykorea-recipe"
DATASET_NAME = "식품안전나라 레시피 DB"
SOURCE_ORGANIZATION = "식품의약품안전처"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="공공데이터 레시피 source import")
    parser.add_argument(
        "--input",
        default="../open-recipe/data/recipes.envcheck.json",
        help="공공데이터 레시피 JSON 파일 경로",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.limit:
        rows = rows[: args.limit]

    with SessionLocal() as db:
        imported = 0
        skipped = 0
        for row in rows:
            source_record_id = str(row.get("id") or "").strip()
            if not source_record_id:
                skipped += 1
                continue
            if _already_exists(db, source_record_id):
                skipped += 1
                continue
            source = _build_source(row, source_record_id)
            if not args.dry_run:
                db.add(source)
            imported += 1

        if not args.dry_run:
            db.commit()
        logger.info(
            "imported=%d, skipped=%d, dry_run=%s",
            imported,
            skipped,
            args.dry_run,
        )


def _already_exists(db: Session, source_record_id: str) -> bool:
    return (
        db.query(RecipeSource)
        .filter(
            RecipeSource.source_dataset_id == DATASET_ID,
            RecipeSource.source_record_id == source_record_id,
        )
        .first()
        is not None
    )


def _build_source(row: dict[str, Any], source_record_id: str) -> RecipeSource:
    content = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return RecipeSource(
        source_type=SOURCE_TYPE,
        source_site=SOURCE_SITE,
        parser_type=PARSER_TYPE,
        source_recipe_id=source_record_id,
        source_record_id=source_record_id,
        source_organization=SOURCE_ORGANIZATION,
        source_dataset_id=DATASET_ID,
        source_dataset_name=DATASET_NAME,
        source_author_name=SOURCE_ORGANIZATION,
        raw_payload=row,
        raw_content_hash=hashlib.sha256(content.encode()).hexdigest(),
        parse_status="NOT_PARSED",
        review_status="PENDING",
        import_status="NOT_IMPORTED",
        collected_at=datetime.now(UTC),
    )


if __name__ == "__main__":
    main()
