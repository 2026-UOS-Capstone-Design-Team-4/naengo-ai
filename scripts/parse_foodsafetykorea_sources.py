"""
공공데이터 foodsafetykorea recipe_sources를 recipe_source_extractions로 파싱합니다.

Usage:
    uv run python scripts/parse_foodsafetykorea_sources.py --limit 100
    uv run python scripts/parse_foodsafetykorea_sources.py --limit 100 --refresh
"""

# ruff: noqa: I001

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.orm import Session, joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import (
    API_KEY,
    BASE_URL,
    MODEL_NAME,
    RECIPE_IMPORT_AI_TIMEOUT_SECONDS,
)
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.models.recipe_source import (
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedLabel,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
    RecipeSourceQualityScore,
)
from app.services.ingestion.foodsafetykorea_ingredient_parser_service import (
    FoodsafetyKoreaIngredientParser,
    foodsafetykorea_ingredient_parser,
)
from app.services.ingestion.recipe_text_rewrite_service import (
    RecipeTextDraft,
    RecipeTextRewriter,
    recipe_text_rewrite_service,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_SITE = "foodsafetykorea"
SOURCE_TYPE = "PUBLIC_DATA"
EXTRACTION_VERSION = "foodsafetykorea-extraction-v1"
DIFFICULTY_MODEL = "gpt-5.4-mini"
VALID_DIFFICULTIES = {"easy", "normal", "hard"}
MAX_COOKING_TIME_MINUTES = 120
_openai_client: OpenAI | None = None
_recipe_metadata_extractor: "AIRecipeMetadataExtractor | None" = None


class ExtractionBuildError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        super().__init__(", ".join(error["code"] for error in errors))


class RecipeMetadata(BaseModel):
    servings: float | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None


class RecipeMetadataOutput(BaseModel):
    servings: float | None = None
    cooking_time_minutes: int | None = None
    kcal_per_serving: int | None = None


class DifficultyEstimator(Protocol):
    def __call__(
        self,
        title: str,
        ingredients: list[RecipeSourceExtractedIngredient],
        steps: list[RecipeSourceExtractedStep],
    ) -> str | None:
        pass


class RecipeMetadataExtractor(Protocol):
    def extract(
        self,
        row: dict[str, Any],
        title: str,
        ingredients: list[RecipeSourceExtractedIngredient],
        steps: list[RecipeSourceExtractedStep],
    ) -> RecipeMetadata:
        pass


class AIRecipeMetadataExtractor:
    def __init__(
        self,
        agent: Agent | None = None,
        model: str = MODEL_NAME,
    ) -> None:
        self._agent = agent or _build_metadata_agent(model)

    def extract(
        self,
        row: dict[str, Any],
        title: str,
        ingredients: list[RecipeSourceExtractedIngredient],
        steps: list[RecipeSourceExtractedStep],
    ) -> RecipeMetadata:
        try:
            result = self._agent.run_sync(
                _metadata_prompt(row, title, ingredients, steps)
            )
        except Exception as exc:
            logger.warning("metadata extraction failed (%s): %s", title, exc)
            return RecipeMetadata()
        cooking_time = _clean_total_time(result.output.cooking_time_minutes)
        kcal_per_serving = (
            _int(result.output.kcal_per_serving)
            if result.output.kcal_per_serving
            else None
        )
        return RecipeMetadata(
            servings=_clean_servings(result.output.servings),
            cooking_time_minutes=cooking_time,
            kcal_per_serving=kcal_per_serving,
        )


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            timeout=RECIPE_IMPORT_AI_TIMEOUT_SECONDS,
        )
    return _openai_client


def _get_recipe_metadata_extractor() -> AIRecipeMetadataExtractor:
    global _recipe_metadata_extractor
    if _recipe_metadata_extractor is None:
        _recipe_metadata_extractor = AIRecipeMetadataExtractor()
    return _recipe_metadata_extractor


def main() -> None:
    parser = argparse.ArgumentParser(description="공공데이터 source extraction 생성")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="기존 extraction이 있어도 삭제 후 다시 생성합니다.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        source_ids = _source_ids(db, limit=args.limit, refresh=args.refresh)

    logger.info("%d개 공공데이터 source extraction 생성 시작", len(source_ids))
    counts: dict[str, int] = {}
    for source_id in source_ids:
        with SessionLocal() as db:
            result = process_source(
                db,
                source_id,
                refresh=args.refresh,
            )
            counts[result] = counts.get(result, 0) + 1
            logger.info("[%s] source_id=%d", result, source_id)

    logger.info("완료: %s", counts)


def _source_ids(db: Session, limit: int, refresh: bool) -> list[int]:
    query = (
        db.query(RecipeSource.source_id)
        .filter(
            RecipeSource.source_type == SOURCE_TYPE,
            RecipeSource.source_site == SOURCE_SITE,
        )
        .order_by(RecipeSource.source_id)
    )
    if not refresh:
        query = query.filter(RecipeSource.parse_status == "NOT_PARSED")
    return [row[0] for row in query.limit(limit).all()]


def process_source(
    db: Session,
    source_id: int,
    ingredient_parser: FoodsafetyKoreaIngredientParser = (
        foodsafetykorea_ingredient_parser
    ),
    text_rewriter: RecipeTextRewriter = recipe_text_rewrite_service,
    refresh: bool = False,
) -> str:
    source = (
        db.query(RecipeSource)
        .options(joinedload(RecipeSource.extraction))
        .filter(RecipeSource.source_id == source_id)
        .first()
    )
    if source is None:
        return "NOT_FOUND"
    if source.extraction is not None and not refresh:
        return "SKIPPED"

    try:
        extraction = build_extraction(
            source.raw_payload,
            ingredient_parser=ingredient_parser,
            text_rewriter=text_rewriter,
        )
    except ExtractionBuildError as exc:
        db.rollback()
        source = db.get(RecipeSource, source_id)
        source.parse_status = "INVALID"
        source.review_status = "PENDING"
        source.validation_errors = exc.errors
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return "INVALID"
    except Exception as exc:
        db.rollback()
        source = db.get(RecipeSource, source_id)
        source.parse_status = "INVALID"
        source.review_status = "PENDING"
        source.validation_errors = [
            {"code": "PUBLIC_DATA_EXTRACTION_FAILED", "message": str(exc)}
        ]
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return "INVALID"

    if source.extraction is not None:
        db.delete(source.extraction)
        db.flush()

    source.review_status = "PENDING"
    source.validation_errors = validate(extraction)
    if source.validation_errors:
        source.parse_status = "INVALID"
        source.extraction_version = EXTRACTION_VERSION
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return source.parse_status

    source.extraction = extraction
    source.parse_status = "PARSED"
    source.extraction_version = EXTRACTION_VERSION
    source.parsed_at = datetime.now(UTC)
    db.commit()
    return source.parse_status


def build_extraction(
    row: dict[str, Any],
    ingredient_parser: FoodsafetyKoreaIngredientParser = (
        foodsafetykorea_ingredient_parser
    ),
    text_rewriter: RecipeTextRewriter = recipe_text_rewrite_service,
    difficulty_estimator: DifficultyEstimator | None = None,
    metadata_extractor: RecipeMetadataExtractor | None = None,
) -> RecipeSourceExtraction:
    raw_extraction = _build_raw_extraction(
        row,
        ingredient_parser,
        difficulty_estimator or estimate_difficulty,
        metadata_extractor or _get_recipe_metadata_extractor(),
    )
    draft = text_rewriter.rewrite(raw_extraction)
    extraction = _apply_draft(raw_extraction, draft)
    if extraction.quality_score is not None:
        extraction.quality_score.rewrite_confidence = 0.80
    return extraction


def _build_raw_extraction(
    row: dict[str, Any],
    ingredient_parser: FoodsafetyKoreaIngredientParser,
    difficulty_estimator: DifficultyEstimator,
    metadata_extractor: RecipeMetadataExtractor,
) -> RecipeSourceExtraction:
    nutrition = row.get("nutrition") if isinstance(row.get("nutrition"), dict) else {}
    title = _text(row.get("name")) or f"공공데이터 레시피 {row.get('id')}"
    ingredients = _ingredients(row, title, ingredient_parser)
    steps = _steps(row)
    _raise_if_missing_required_structure(ingredients, steps)

    metadata = metadata_extractor.extract(row, title, ingredients, steps)
    difficulty = _infer_difficulty(len(ingredients), len(steps))
    if difficulty is None:
        difficulty = difficulty_estimator(title, ingredients, steps)

    extraction = RecipeSourceExtraction(
        title=title,
        summary=_summary(row),
        description=_description(row),
        servings=metadata.servings,
        cooking_time_minutes=metadata.cooking_time_minutes,
        kcal_per_serving=metadata.kcal_per_serving,
        serving_weight_grams=_decimal(row.get("serving_weight")),
        carbohydrate_grams=_decimal(nutrition.get("carbohydrate")),
        protein_grams=_decimal(nutrition.get("protein")),
        fat_grams=_decimal(nutrition.get("fat")),
        sodium_milligrams=_decimal(nutrition.get("sodium")),
        nutrition_source="SOURCE",
        nutrition_raw=nutrition,
        difficulty=difficulty,
        source_main_image_url=_text(row.get("image_large_url")),
        source_thumbnail_url=_text(row.get("image_small_url")),
        content_hash=_content_hash(row),
    )
    extraction.ingredients = ingredients
    extraction.steps = steps
    extraction.labels = _labels(row)
    extraction.quality_score = _build_quality_score(extraction, metadata)
    return extraction


def _raise_if_missing_required_structure(
    ingredients: list[RecipeSourceExtractedIngredient],
    steps: list[RecipeSourceExtractedStep],
) -> None:
    errors = []
    if not ingredients:
        errors.append(
            {"code": "MISSING_INGREDIENTS", "message": "ingredients are required."}
        )
    if not steps:
        errors.append({"code": "MISSING_STEPS", "message": "steps are required."})
    if errors:
        raise ExtractionBuildError(errors)


def _build_metadata_agent(model_name: str) -> Agent:
    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(api_key=API_KEY, base_url=BASE_URL),
    )
    return Agent(
        model,
        output_type=RecipeMetadataOutput,
        system_prompt=_METADATA_SYSTEM_PROMPT,
        model_settings={"timeout": RECIPE_IMPORT_AI_TIMEOUT_SECONDS},
    )


def _metadata_prompt(
    row: dict[str, Any],
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    steps: list[RecipeSourceExtractedStep],
) -> str:
    nutrition = row.get("nutrition") if isinstance(row.get("nutrition"), dict) else {}
    payload = {
        "title": title,
        "description": _text(row.get("description")),
        "category": _text(row.get("category")),
        "method": _text(row.get("method")),
        "raw_serving_weight": _text(row.get("serving_weight")),
        "raw_ingredients": _text(row.get("ingredients")),
        "raw_nutrition": {
            "calories": nutrition.get("calories"),
            "carbohydrate_g": nutrition.get("carbohydrate"),
            "protein_g": nutrition.get("protein"),
            "fat_g": nutrition.get("fat"),
            "sodium_mg": nutrition.get("sodium"),
        },
        "ingredients": [
            {
                "name": ingredient.name,
                "amount_text": ingredient.amount_text,
                "raw_text": ingredient.raw_text,
            }
            for ingredient in ingredients
        ],
        "steps": [
            {
                "step_no": step.step_no,
                "instruction": step.instruction,
            }
            for step in steps
        ],
        "raw_manual_steps": row.get("manual_steps"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _apply_draft(
    extraction: RecipeSourceExtraction,
    draft: RecipeTextDraft,
) -> RecipeSourceExtraction:
    extraction.title = draft.title
    extraction.summary = draft.summary
    extraction.description = draft.description
    for index, ingredient in enumerate(draft.ingredients):
        target = extraction.ingredients[index]
        target.group_name = ingredient.group_name
        target.name = ingredient.name
        target.normalized_name = ingredient.normalized_name or ingredient.name
        target.amount_text = ingredient.amount_text
        target.note = ingredient.note
        target.raw_text = ingredient.raw_text
        target.is_optional = ingredient.is_optional
    for index, step in enumerate(draft.steps):
        target = extraction.steps[index]
        target.instruction = step.instruction
        target.tip = step.tip
    tip_labels = [
        label for label in list(extraction.labels) if label.label_type == "TIP"
    ]
    for label in tip_labels:
        extraction.labels.remove(label)
    for index, tip_text in enumerate(draft.tips, start=1):
        extraction.labels.append(
            RecipeSourceExtractedLabel(
                label_type="TIP",
                label_value=tip_text,
                source="AI",
                sort_order=200 + index,
            )
        )
    return extraction


def validate(extraction: RecipeSourceExtraction) -> list[dict[str, str]]:
    errors = []
    if not extraction.title:
        errors.append({"code": "MISSING_TITLE", "message": "title is required."})
    if not extraction.ingredients:
        errors.append(
            {"code": "MISSING_INGREDIENTS", "message": "ingredients are required."}
        )
    if not extraction.steps:
        errors.append({"code": "MISSING_STEPS", "message": "steps are required."})
    if not extraction.servings:
        errors.append({"code": "MISSING_SERVINGS", "message": "servings is required."})
    if not extraction.cooking_time_minutes:
        errors.append(
            {
                "code": "MISSING_COOKING_TIME",
                "message": "cooking_time_minutes is required.",
            }
        )
    if not any(label.label_type == "CATEGORY" for label in extraction.labels):
        errors.append({"code": "MISSING_CATEGORY", "message": "category is required."})
    return errors


def _build_quality_score(
    extraction: RecipeSourceExtraction,
    metadata: RecipeMetadata,
) -> RecipeSourceQualityScore:
    metadata_fields = {
        "servings": metadata.servings,
        "cooking_time_minutes": metadata.cooking_time_minutes,
        "kcal_per_serving": metadata.kcal_per_serving,
    }
    estimated_fields = [key for key, value in metadata_fields.items() if value]
    nutrition_values = [
        extraction.kcal_per_serving,
        extraction.serving_weight_grams,
        extraction.carbohydrate_grams,
        extraction.protein_grams,
        extraction.fat_grams,
        extraction.sodium_milligrams,
    ]
    return RecipeSourceQualityScore(
        completeness_score=_completeness_score(extraction),
        parse_confidence=0.80,
        ingredient_confidence=0.85 if extraction.ingredients else 0.0,
        metadata_confidence=0.70 if estimated_fields else 0.0,
        rewrite_confidence=None,
        nutrition_confidence=(
            0.95 if any(value is not None for value in nutrition_values) else None
        ),
        estimated_fields=estimated_fields,
        validation_summary=[],
        quality_notes={
            "metadata_policy": "explicit_or_estimated",
            "source": "foodsafetykorea_parser",
        },
    )


def _completeness_score(extraction: RecipeSourceExtraction) -> float:
    checks = [
        bool(extraction.title),
        bool(extraction.summary or extraction.description),
        bool(extraction.servings),
        bool(extraction.cooking_time_minutes),
        bool(extraction.ingredients),
        bool(extraction.steps),
        extraction.difficulty in VALID_DIFFICULTIES,
        any(label.label_type == "CATEGORY" for label in extraction.labels),
    ]
    return round(sum(checks) / len(checks), 2)


def _ingredients(
    row: dict[str, Any],
    title: str,
    ingredient_parser: FoodsafetyKoreaIngredientParser,
) -> list[RecipeSourceExtractedIngredient]:
    raw = _text(row.get("ingredients")) or ""
    parsed = ingredient_parser.parse(title, raw)
    return [
        RecipeSourceExtractedIngredient(
            group_name=item.group_name,
            name=item.name,
            normalized_name=item.normalized_name or item.name,
            amount_text=item.amount_text,
            quantity=_decimal(item.quantity),
            unit=item.unit,
            note=item.note,
            raw_text=item.raw_text,
            is_optional=item.is_optional,
            sort_order=index,
        )
        for index, item in enumerate(parsed, start=1)
    ]


def _steps(row: dict[str, Any]) -> list[RecipeSourceExtractedStep]:
    manual_steps = row.get("manual_steps")
    if not isinstance(manual_steps, list):
        return []
    steps = []
    for index, item in enumerate(manual_steps, start=1):
        if not isinstance(item, dict):
            continue
        instruction = _clean_step(_text(item.get("description")) or "")
        if not instruction:
            continue
        steps.append(
            RecipeSourceExtractedStep(
                step_no=int(item.get("step") or index),
                instruction=instruction,
                source_image_url=_text(item.get("image_url")),
                raw_text=_text(item.get("description")),
                sort_order=index,
            )
        )
    return steps


def _labels(row: dict[str, Any]) -> list[RecipeSourceExtractedLabel]:
    labels = []
    values = [
        ("CATEGORY", row.get("category")),
        ("TAG", row.get("method")),
        ("TIP", row.get("low_sodium_tip")),
    ]
    hash_tag = _text(row.get("hash_tag"))
    if hash_tag:
        values.extend(("TAG", tag) for tag in re.split(r"[,#\s]+", hash_tag) if tag)

    for index, (label_type, value) in enumerate(values, start=1):
        text = _text(value)
        if not text:
            continue
        labels.append(
            RecipeSourceExtractedLabel(
                label_type=label_type,
                label_value=text,
                source="SCRAPE",
                confidence_score=0.85,
                sort_order=index,
            )
        )
    return labels


def _summary(row: dict[str, Any]) -> str | None:
    name = _text(row.get("name"))
    category = _text(row.get("category"))
    method = _text(row.get("method"))
    parts = [part for part in [category, method] if part]
    if not name:
        return None
    if not parts:
        return f"{name} 레시피"
    return f"{' / '.join(parts)} 방식의 {name} 레시피"


def _description(row: dict[str, Any]) -> str | None:
    return _text(row.get("description"))


def _infer_difficulty(ingredient_count: int, step_count: int) -> str | None:
    if ingredient_count <= 0 or step_count <= 0:
        return None
    if ingredient_count <= 5 and step_count <= 4:
        return "easy"
    if ingredient_count >= 15 or step_count >= 8:
        return "hard"
    return None


def estimate_difficulty(
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    steps: list[RecipeSourceExtractedStep],
) -> str | None:
    if not ingredients or not steps:
        return None
    ingredient_lines = "\n".join(
        f"- {ingredient.name} {ingredient.amount_text or ''}".strip()
        for ingredient in ingredients
    )
    step_lines = "\n".join(f"{step.step_no}. {step.instruction}" for step in steps[:5])
    prompt = (
        f"레시피 '{title}'의 조리 난이도를 판정해 주세요.\n"
        f"재료:\n{ingredient_lines}\n\n"
        f"조리 단계:\n{step_lines}\n\n"
        "easy(간단), normal(보통), hard(어려움) 중 하나만 답하세요."
    )
    try:
        response = _get_openai_client().chat.completions.create(
            model=DIFFICULTY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=20,
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        text = content.strip().lower()
        for difficulty in ("easy", "normal", "hard"):
            if difficulty in text:
                return difficulty
    except Exception as exc:
        logger.warning("difficulty estimation failed (%s): %s", title, exc)
    return None


def _clean_step(value: str) -> str:
    return re.sub(r"^\s*\d+\.\s*", "", value).strip()


def _content_hash(row: dict[str, Any]) -> str:
    parts = [
        _text(row.get("name")),
        _text(row.get("ingredients")),
        json.dumps(row.get("manual_steps") or [], ensure_ascii=False, sort_keys=True),
    ]
    return hashlib.sha256(" ".join(part for part in parts if part).encode()).hexdigest()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    decimal = _decimal(value)
    return int(decimal) if decimal is not None else None


def _clean_servings(value: Any) -> float | None:
    decimal = _decimal(value)
    if decimal is None or decimal <= 0:
        return None
    return float(decimal.quantize(Decimal("0.1")))


def _clean_total_time(value: Any) -> int | None:
    decimal = _decimal(value)
    if decimal is None or decimal <= 0:
        return None
    minutes = int(decimal)
    return minutes if minutes <= MAX_COOKING_TIME_MINUTES else None


def _decimal(value: Any) -> Decimal | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


_METADATA_SYSTEM_PROMPT = """
You extract serving count, cooking time, and kcal_per_serving from public
recipe data.

Return only the structured output fields:
- servings: number of servings/portions. Use null when the source does not imply it.
- cooking_time_minutes: practical app-facing cooking minutes needed from preparation
  through serving. Use null when the source does not mention or strongly imply time.
- kcal_per_serving: estimated kilocalories per single serving. Use null when the
  recipe has no nutrition data and the dish type gives too little evidence to estimate.

Rules:
- Prefer explicit serving and time values when present.
- If servings are not explicit, estimate a practical serving count from ingredient
  quantities, dish type, liquid amount, and recipe scale.
- Do not derive servings from kcal or nutrition values alone.
- If cooking time is not explicit, estimate a practical cooking time from cooking
  method and step descriptions.
- Do not invent blind defaults such as always 1 serving or always 30 minutes; use
  the recipe evidence.
- Include washing, cutting, boiling, baking, simmering, and ordinary short rests.
- Do not count long passive waits at full length. Overnight salting, multi-hour
  steeping, marinating, freezing, chilling, or storage should be treated as advance
  prep and excluded from the app-facing cooking time.
- For recipes with long passive waits, estimate the active handling plus active
  heating/cooking time needed in one cooking session.
- If the practical app-facing cooking time is over 120 minutes, use null.
- If individual step durations are present, cooking_time_minutes may be the sum of
  active durations plus clearly stated short prep/rest time.
- If the text contains a range, use a practical midpoint rounded down to minutes.
- Output positive values only; use null only when the recipe has too little evidence
  to make a reasonable estimate.
- For kcal_per_serving: if raw_nutrition.calories is present, divide it by the
  estimated servings count to get kcal_per_serving (round to nearest integer).
  If raw_nutrition.calories is absent or null, estimate per-serving kcal from the
  ingredient list, quantities, and dish type using nutritional knowledge.
  Use null only when there is genuinely insufficient evidence.
""".strip()


if __name__ == "__main__":
    main()
