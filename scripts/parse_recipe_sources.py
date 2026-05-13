"""
recipe_sources 파싱 CLI.

Usage:
    uv run python scripts/normalize_recipe_sources.py \
        --collection-status COLLECTED --limit 300
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI

from app.core.config import API_KEY, BASE_URL
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe
from app.models.recipe_source import (
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedLabel,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
)
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CALORIE_MODEL = "gpt-5.4-mini"
_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _openai_client


def estimate_calories(
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    servings: float | None,
) -> int | None:
    if not ingredients:
        return None
    ingredient_lines = "\n".join(
        f"- {ing.name} {ing.amount_text or ''}".strip()
        for ing in ingredients
    )
    servings_text = f"{int(servings)}인분" if servings else "인분 정보 없음"
    prompt = (
        f"한국 요리 '{title}'의 1인분 칼로리를 추정해줘.\n"
        f"총 분량: {servings_text}\n"
        f"재료:\n{ingredient_lines}\n\n"
        "1인분 기준 총 칼로리를 정수(kcal)로만 답해. 단위 없이 숫자만."
    )
    try:
        resp = _get_openai_client().chat.completions.create(
            model=CALORIE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        numbers = re.findall(r"\d+", text)
        if numbers:
            return int(numbers[0])
    except Exception as exc:
        logger.warning("칼로리 추정 실패 (%s): %s", title, exc)
    return None

VALID_DIFFICULTIES = {"easy", "normal", "hard"}


def parse_servings(raw: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", raw or "")
    return float(match.group(1)) if match else None


def parse_cooking_time(raw: str) -> int | None:
    total = 0
    for hours in re.findall(r"(\d+)\s*시간", raw or ""):
        total += int(hours) * 60
    for minutes in re.findall(r"(\d+)\s*분", raw or ""):
        total += int(minutes)
    return total if total else None


def infer_difficulty(cooking_time: int | None, ingredient_count: int) -> str:
    if cooking_time is None:
        return "normal"
    if cooking_time <= 20 and ingredient_count <= 5:
        return "easy"
    if cooking_time >= 60 or ingredient_count >= 15:
        return "hard"
    return "normal"


def infer_category(raw: dict[str, Any]) -> list[str]:
    title = raw.get("title", "")
    tags = raw.get("tags", [])
    text = " ".join([title, *tags])

    # 구체적인 복합어를 먼저 체크해 오매칭 방지
    rules: list[tuple[str, list[str]]] = [
        ("베이킹/디저트", ["쿠키", "케이크", "베이킹", "마카롱", "타르트", "머핀", "스콘"]),
        ("밥/덮밥", ["비빔밥", "볶음밥", "덮밥", "솥밥", "오므라이스"]),
        ("볶음", ["볶음", "볶기"]),
        ("국/찌개", ["찌개", "미역국", "된장국", "순두부"]),
        ("구이", ["구이", "굽기"]),
        ("무침", ["무침"]),
        ("조림", ["조림"]),
        ("찜", ["찜"]),
        ("회", ["육회", "회무침", "생선회"]),
        ("샐러드", ["샐러드"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return [category]

    # 복합어 패턴: 2글자 이상 한글 + "전" (파전·두릅전·김치전 등, "버전" 제외)
    if re.search(r"[가-힣]{2,}전", text):
        return ["전/부침"]
    # "국"으로 끝나는 복합어 (미역국끓이기 등)
    if re.search(r"[가-힣]+국", text):
        return ["국/찌개"]
    # "탕"
    if "탕" in text:
        return ["국/찌개"]
    # "밥"으로 끝나는 복합어 (곤드레밥, 잡채밥 등)
    if re.search(r"[가-힣]+밥", text):
        return ["밥/덮밥"]
    # "빵"
    if "빵" in text:
        return ["베이킹/디저트"]

    return ["기타"]


def build_extraction(raw: dict[str, Any]) -> RecipeSourceExtraction:
    ingredients = [
        RecipeSourceExtractedIngredient(
            group_name=item.get("group_name"),
            name=item.get("name", ""),
            normalized_name=item.get("name", ""),
            amount_text=item.get("amount"),
            raw_text=item.get("raw_text"),
            sort_order=index,
        )
        for index, item in enumerate(raw.get("ingredients", []), start=1)
        if isinstance(item, dict) and item.get("name")
    ]
    cooking_time = parse_cooking_time(raw.get("cooking_time_raw", ""))
    labels = [
        RecipeSourceExtractedLabel(
            label_type="TAG",
            label_value=tag,
            source="SCRAPE",
            sort_order=index,
        )
        for index, tag in enumerate(raw.get("tags", []), start=1)
    ]
    labels.extend(
        RecipeSourceExtractedLabel(
            label_type="CATEGORY",
            label_value=category,
            source="RULE",
            sort_order=100 + index,
        )
        for index, category in enumerate(infer_category(raw), start=1)
    )
    labels.extend(
        RecipeSourceExtractedLabel(
            label_type="TIP",
            label_value=tip,
            source="SCRAPE",
            sort_order=200 + index,
        )
        for index, tip in enumerate(raw.get("tips", []), start=1)
    )

    title = raw.get("title", "")
    servings = parse_servings(raw.get("servings_raw", ""))
    calories = estimate_calories(title, ingredients, servings)

    return RecipeSourceExtraction(
        title=title,
        summary=raw.get("description"),
        description=raw.get("description") or title,
        servings=servings,
        total_time_minutes=cooking_time,
        difficulty=infer_difficulty(cooking_time, len(ingredients)),
        calories=calories,
        source_main_image_url=raw.get("image_url"),
        content_hash=hashlib.sha256(
            json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        ingredients=ingredients,
        steps=[
            RecipeSourceExtractedStep(
                step_no=int(step.get("step_no") or index),
                instruction=step.get("instruction", ""),
                source_image_url=step.get("image_url"),
                sort_order=index,
            )
            for index, step in enumerate(raw.get("instructions", []), start=1)
            if isinstance(step, dict) and step.get("instruction")
        ],
        labels=labels,
    )


def validate(extraction: RecipeSourceExtraction) -> list[dict[str, str]]:
    errors = []
    if not extraction.title:
        errors.append({"code": "MISSING_TITLE", "message": "제목이 없습니다."})
    if not extraction.ingredients:
        errors.append({"code": "MISSING_INGREDIENTS", "message": "재료가 없습니다."})
    if not extraction.steps:
        errors.append({"code": "MISSING_STEPS", "message": "조리 단계가 없습니다."})
    if not extraction.servings:
        errors.append({"code": "MISSING_SERVINGS", "message": "인분 정보가 없습니다."})
    if not extraction.total_time_minutes:
        errors.append(
            {"code": "MISSING_TOTAL_TIME", "message": "조리 시간이 없습니다."}
        )
    if extraction.difficulty not in VALID_DIFFICULTIES:
        errors.append(
            {
                "code": "INVALID_DIFFICULTY",
                "message": "난이도가 올바르지 않습니다.",
            }
        )
    if not any(label.label_type == "CATEGORY" for label in extraction.labels):
        errors.append({"code": "MISSING_CATEGORY", "message": "카테고리가 없습니다."})
    return errors


def is_duplicate(db, source: RecipeSource, extraction: RecipeSourceExtraction) -> bool:
    if (
        db.query(RecipeSource)
        .join(RecipeSourceExtraction)
        .filter(
            RecipeSourceExtraction.content_hash == extraction.content_hash,
            RecipeSource.source_id != source.source_id,
        )
        .first()
    ):
        return True

    return bool(
        source.source_url
        and db.query(Recipe).filter(Recipe.source_url == source.source_url).first()
    )


def process_source(db, source: RecipeSource) -> str:
    try:
        extraction = build_extraction(source.raw_payload)
    except Exception as exc:
        logger.warning("파싱 실패 (source_id=%d): %s", source.source_id, exc)
        source.parse_status = "INVALID"
        source.validation_errors = [{"code": "PARSE_ERROR", "message": str(exc)}]
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return "INVALID"

    # 기존 extraction이 있으면 삭제 후 교체
    if source.extraction is not None:
        db.delete(source.extraction)
        db.flush()

    source.raw_content_hash = extraction.content_hash
    source.extraction = extraction
    source.parsed_at = datetime.now(UTC)

    if is_duplicate(db, source, extraction):
        source.parse_status = "DUPLICATE"
        source.review_status = "PENDING"
        db.commit()
        return "DUPLICATE"

    errors = validate(extraction)
    source.validation_errors = errors
    source.parse_status = "REVIEW_REQUIRED" if errors else "PARSED"
    source.review_status = "PENDING"

    db.commit()
    return source.parse_status


def main() -> None:
    parser = argparse.ArgumentParser(description="recipe_sources 파싱")
    parser.add_argument("--collection-status", default="COLLECTED")
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        sources = (
            db.query(RecipeSource)
            .filter(RecipeSource.collection_status == args.collection_status)
            .limit(args.limit)
            .all()
        )
        logger.info("%d개 source 파싱 시작", len(sources))

        counts: dict[str, int] = {}
        for source in sources:
            result = process_source(db, source)
            counts[result] = counts.get(result, 0) + 1
            logger.info("[%s] source_id=%d", result, source.source_id)

        logger.info("완료: %s", counts)
    finally:
        db.close()


if __name__ == "__main__":
    main()
