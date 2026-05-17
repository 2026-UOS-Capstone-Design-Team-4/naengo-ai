"""
10000recipe recipe_sources parsing CLI.

Usage:
    uv run python scripts/parse_10000recipe_sources.py --limit 300
    uv run python scripts/parse_10000recipe_sources.py --limit 300 --refresh
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI

from app.core.config import API_KEY, BASE_URL, RECIPE_IMPORT_AI_TIMEOUT_SECONDS
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe
from app.models.recipe_source import (
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedLabel,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
    RecipeSourceQualityScore,
)
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.ingestion.ingredient_amount_note_service import (
    move_amount_parentheses_to_note,
)
from app.services.ingestion.recipe_text_rewrite_service import (
    RecipeTextDraft,
    RecipeTextRewriter,
    recipe_text_rewrite_service,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

METADATA_MODEL = "gpt-5.4-mini"
EXTRACTION_VERSION = "10000recipe-extraction-v1"
SOURCE_SITE = "10000recipe"
SOURCE_TYPE = "WEB_SCRAPE"
VALID_DIFFICULTIES = {"easy", "normal", "hard"}
MAX_COOKING_TIME_MINUTES = 120
_openai_client: OpenAI | None = None


class ExtractionBuildError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        super().__init__(", ".join(error["code"] for error in errors))


@dataclass(frozen=True)
class EstimatedRecipeMetadata:
    kcal_per_serving: int | None = None
    cooking_time_minutes: int | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL or None,
            timeout=RECIPE_IMPORT_AI_TIMEOUT_SECONDS,
        )
    return _openai_client


def estimate_recipe_metadata(
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    steps: list[RecipeSourceExtractedStep],
    servings: float | None,
    stated_total_time: int | None,
) -> EstimatedRecipeMetadata:
    if not ingredients or not steps:
        return EstimatedRecipeMetadata(
            cooking_time_minutes=_clean_cooking_time(stated_total_time)
        )
    ingredient_lines = "\n".join(
        f"- {ingredient.name} {ingredient.amount_text or ''}".strip()
        for ingredient in ingredients
    )
    step_lines = "\n".join(f"{step.step_no}. {step.instruction}" for step in steps[:8])
    servings_text = f"{int(servings)} servings" if servings else "unknown servings"
    prompt = (
        f"Estimate recipe metadata for Korean recipe '{title}'.\n"
        f"Total servings: {servings_text}\n"
        f"Ingredients:\n{ingredient_lines}\n\n"
        f"Steps:\n{step_lines}\n\n"
        f"Stated total time: {stated_total_time or 'unknown'} minutes\n\n"
        "Return only JSON with keys: kcal_per_serving, cooking_time_minutes. "
        "kcal_per_serving must be a practical positive integer kcal per serving; "
        "do not return null for kcal_per_serving when ingredients exist. "
        "cooking_time_minutes should be practical app-facing cooking minutes "
        "from preparation through serving. Do not count long passive waits "
        "such as overnight salting, multi-hour marinating, chilling, freezing, "
        "or storage at full length; estimate active handling plus active "
        "heating/cooking time. Use null only when uncertain."
    )
    try:
        response = _get_openai_client().chat.completions.create(
            model=METADATA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=120,
            temperature=0,
        )
        text = response.choices[0].message.content or ""
        payload = _parse_json_object(text)
        kcal = _positive_int(payload.get("kcal_per_serving"))
        if kcal is None:
            kcal = _estimate_kcal_per_serving_only(title, ingredients, servings)
        return EstimatedRecipeMetadata(
            kcal_per_serving=kcal,
            cooking_time_minutes=_clean_cooking_time(
                _positive_int(payload.get("cooking_time_minutes"))
                or stated_total_time
            ),
        )
    except Exception as exc:
        logger.warning("metadata estimation failed (%s): %s", title, exc)
    return EstimatedRecipeMetadata(
        cooking_time_minutes=_clean_cooking_time(stated_total_time)
    )


def estimate_kcal_per_serving(
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    servings: float | None,
) -> int | None:
    metadata = estimate_recipe_metadata(title, ingredients, [], servings, None)
    return metadata.kcal_per_serving or _estimate_kcal_per_serving_only(
        title,
        ingredients,
        servings,
    )


def _estimate_kcal_per_serving_only(
    title: str,
    ingredients: list[RecipeSourceExtractedIngredient],
    servings: float | None,
) -> int | None:
    if not ingredients:
        return None
    ingredient_lines = "\n".join(
        f"- {ingredient.name} {ingredient.amount_text or ''}".strip()
        for ingredient in ingredients
    )
    servings_text = f"{int(servings)} servings" if servings else "unknown servings"
    prompt = (
        f"Estimate kcal per serving for Korean recipe '{title}'.\n"
        f"Total servings: {servings_text}\n"
        f"Ingredients:\n{ingredient_lines}\n\n"
        "Return only one practical integer kcal value. Do not return null."
    )
    try:
        response = _get_openai_client().chat.completions.create(
            model=METADATA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=10,
            temperature=0,
        )
        text = response.choices[0].message.content or ""
        numbers = re.findall(r"\d+", text)
        if numbers:
            return int(numbers[0])
    except Exception as exc:
        logger.warning("kcal_per_serving estimation failed (%s): %s", title, exc)
    return None


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _positive_int(value: Any) -> int | None:
    try:
        integer = int(float(value))
    except (TypeError, ValueError):
        return None
    return integer if integer > 0 else None


def _clean_cooking_time(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    return value if value <= MAX_COOKING_TIME_MINUTES else None


def parse_servings(raw: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", raw or "")
    return float(match.group(1)) if match else None


def parse_cooking_time(raw: str) -> int | None:
    total = 0
    for hours in re.findall(r"(\d+)\s*시간", raw or ""):
        total += int(hours) * 60
    for minutes in re.findall(r"(\d+)\s*분", raw or ""):
        total += int(minutes)
    return _clean_cooking_time(total) if total else None


def infer_difficulty(cooking_time: int | None, ingredient_count: int) -> str | None:
    if cooking_time is None:
        return None
    if cooking_time <= 20 and ingredient_count <= 5:
        return "easy"
    if cooking_time >= 60 or ingredient_count >= 15:
        return "hard"
    return "normal"


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
        f"Classify Korean recipe '{title}' difficulty.\n"
        f"Ingredients:\n{ingredient_lines}\n\n"
        f"Steps:\n{step_lines}\n\n"
        "Return only one of: easy, normal, hard."
    )
    try:
        response = _get_openai_client().chat.completions.create(
            model=METADATA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=20,
            temperature=0,
        )
        text = (response.choices[0].message.content or "").strip().lower()
        for difficulty in ("easy", "normal", "hard"):
            if difficulty in text:
                return difficulty
    except Exception as exc:
        logger.warning("difficulty estimation failed (%s): %s", title, exc)
    return None


def infer_category(raw: dict[str, Any]) -> list[str]:
    title = raw.get("title", "")
    tags = raw.get("tags", [])
    text = " ".join([title, *tags])
    rules: list[tuple[str, list[str]]] = [
        (
            "베이킹/디저트",
            ["쿠키", "케이크", "베이킹", "마카롱", "타르트", "머핀", "스콘"],
        ),
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
    if re.search(r"[가-힣]{2,}전", text):
        return ["전/부침"]
    if re.search(r"[가-힣]+국", text) or "탕" in text:
        return ["국/찌개"]
    if re.search(r"[가-힣]+밥", text):
        return ["밥/덮밥"]
    if "빵" in text:
        return ["베이킹/디저트"]
    return ["기타"]


_PAREN_STRIP = re.compile(r"[\(（][^\)）]*[\)）]")
_FRACTION_MAP = {"½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4"}
_FRACTION_KOREAN = re.compile(r"^(\d+)\s*과\s*(\d+/\d+)")
_AMOUNT_PATTERN = re.compile(
    r"^(\d+(?:[./]\d+)?(?:\s*~\s*\d+(?:[./]\d+)?)?)\s*([가-힣a-zA-Z]+)?$"
)
_OPTIONAL_KEYWORDS = ("선택", "없어도", "생략", "빼도", "선택재료", "생략가능")
_UNIT_REPLACEMENTS: list[tuple[str, str]] = sorted(
    [
        ("테이블스푼", "T"),
        ("큰 술", "T"),
        ("큰술", "T"),
        ("스푼", "T"),
        ("tbsp", "T"),
        ("Ts", "T"),
        ("TS", "T"),
        ("작은스푼", "t"),
        ("작은 술", "t"),
        ("작은술", "t"),
        ("tsp", "t"),
        ("ts", "t"),
        ("컵분량", "컵"),
        ("cup", "컵"),
        ("Cup", "컵"),
    ],
    key=lambda item: -len(item[0]),
)
_PREP_PREFIX = re.compile(
    r"^(다진|채썬|채 썬|얇게 썬|깍둑썬|깍둑 썬|슬라이스한|으깬|"
    r"볶은|구운|데친|삶은|마른|건)\s+"
)


def _normalize_ingredient_name(name: str) -> str:
    cleaned = _PAREN_STRIP.sub("", name).strip()
    return (cleaned or name).strip()[:100]


def _parse_is_optional(name: str) -> bool:
    for paren in _PAREN_STRIP.findall(name):
        inner = paren.strip("()（）")
        if any(keyword in inner for keyword in _OPTIONAL_KEYWORDS):
            return True
    return False


def _parse_note_from_name(name: str, amount_note: str | None = None) -> str | None:
    notes = []
    for paren in _PAREN_STRIP.findall(name):
        inner = paren.strip("()（）").strip()
        if inner:
            notes.append(inner)
    clean = _PAREN_STRIP.sub("", name).strip()
    match = _PREP_PREFIX.match(clean)
    if match:
        notes.insert(0, match.group(0).strip())
    if amount_note:
        notes.append(amount_note)
    return ", ".join(notes) if notes else None


def _normalize_amount_text(text: str | None) -> str | None:
    if not text:
        return None
    normalized = text.strip()
    for fraction, replacement in _FRACTION_MAP.items():
        normalized = normalized.replace(fraction, replacement)
    for old, new in _UNIT_REPLACEMENTS:
        if re.search(r"[가-힣]", old):
            normalized = normalized.replace(old, new)
        else:
            normalized = re.sub(
                rf"(?<![A-Za-z]){re.escape(old)}(?![A-Za-z])",
                new,
                normalized,
            )
    normalized = re.sub(r"(\d)\s+([가-힣a-zA-Z])", r"\1\2", normalized)
    normalized = re.sub(r"\s*분량\s*$", "", normalized).strip()
    normalized = re.sub(r"\s*\(\s*", "(", normalized)
    normalized = re.sub(r"\s*\)\s*", ")", normalized)
    if normalized in ("약간", "조금", "소량"):
        return "약간"
    if normalized in ("적당량", "적당히", "기호에 따라", "적절히"):
        return "적당량"
    return normalized or None


def _safe_fraction(value: str) -> float | None:
    match = _FRACTION_KOREAN.match(value.strip())
    if match:
        try:
            return int(match.group(1)) + float(Fraction(match.group(2)))
        except Exception:
            pass
    try:
        return float(Fraction(value))
    except Exception:
        return None


def _parse_amount(amount_text: str | None) -> tuple[float | None, str | None]:
    if not amount_text:
        return None, None
    text = amount_text.strip()
    for fraction, replacement in _FRACTION_MAP.items():
        text = text.replace(fraction, replacement)
    korean_fraction = _FRACTION_KOREAN.match(text)
    if korean_fraction:
        quantity = _safe_fraction(text[: korean_fraction.end()])
        unit_part = text[korean_fraction.end() :].strip()
        unit_match = re.match(r"^([가-힣a-zA-Z]+)", unit_part)
        return quantity, (unit_match.group(1) if unit_match else None)
    match = _AMOUNT_PATTERN.match(text)
    if not match:
        return None, None
    quantity_text, unit = match.group(1), match.group(2)
    if "~" in quantity_text:
        parts = re.split(r"\s*~\s*", quantity_text)
        left = _safe_fraction(parts[0])
        right = _safe_fraction(parts[-1])
        quantity = (
            (left + right) / 2 if left is not None and right is not None else None
        )
    else:
        quantity = _safe_fraction(quantity_text)
    return quantity, (unit or None)


def _normalize_parsley_family_unit(
    name: str,
    amount_text: str | None,
    unit: str | None,
) -> tuple[str | None, str | None]:
    if "파슬리" not in name:
        return amount_text, unit
    if amount_text:
        amount_text = amount_text.replace("뿌리", "대")
    if unit == "뿌리":
        unit = "대"
    return amount_text, unit


def build_extraction(raw: dict[str, Any]) -> RecipeSourceExtraction:
    ingredients = []
    for index, item in enumerate(raw.get("ingredients", []), start=1):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        raw_name = item.get("name", "")
        amount_note = move_amount_parentheses_to_note(
            _normalize_amount_text(item.get("amount") or None)
        )
        amount_text = amount_note.amount_text
        quantity, unit = _parse_amount(amount_text)
        amount_text, unit = _normalize_parsley_family_unit(raw_name, amount_text, unit)
        normalized = _normalize_ingredient_name(raw_name)
        raw_text = f"{normalized} {amount_text}".strip() if amount_text else normalized
        ingredients.append(
            RecipeSourceExtractedIngredient(
                group_name=item.get("group_name"),
                name=raw_name[:100],
                normalized_name=normalized,
                amount_text=amount_text,
                quantity=quantity,
                unit=unit,
                note=_parse_note_from_name(raw_name, amount_note.note),
                raw_text=raw_text,
                is_optional=_parse_is_optional(raw_name),
                sort_order=index,
            )
        )

    steps = [
        RecipeSourceExtractedStep(
            step_no=int(step.get("step_no") or index),
            instruction=step.get("instruction", ""),
            raw_text=step.get("instruction") or None,
            source_image_url=step.get("image_url"),
            sort_order=index,
        )
        for index, step in enumerate(raw.get("instructions", []), start=1)
        if isinstance(step, dict) and step.get("instruction")
    ]
    _raise_if_missing_required_structure(ingredients, steps)

    cooking_time = parse_cooking_time(raw.get("cooking_time_raw", ""))
    title = raw.get("title", "")
    servings = parse_servings(raw.get("servings_raw", ""))
    difficulty = infer_difficulty(cooking_time, len(ingredients))
    if difficulty is None:
        difficulty = estimate_difficulty(title, ingredients, steps)

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

    metadata = estimate_recipe_metadata(
        title,
        ingredients,
        steps,
        servings,
        cooking_time,
    )
    if metadata.kcal_per_serving is None:
        raise ValueError("kcal_per_serving could not be estimated.")

    extraction = RecipeSourceExtraction(
        title=title,
        summary=raw.get("description"),
        description=raw.get("description") or title,
        servings=servings,
        cooking_time_minutes=metadata.cooking_time_minutes or cooking_time,
        difficulty=difficulty,
        kcal_per_serving=metadata.kcal_per_serving,
        source_main_image_url=raw.get("image_url"),
        content_hash=hashlib.sha256(
            json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        ingredients=ingredients,
        steps=steps,
        labels=labels,
    )
    extraction.quality_score = _build_quality_score(extraction)
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


def validate(extraction: RecipeSourceExtraction) -> list[dict[str, str]]:
    errors = []
    if not extraction.title:
        errors.append({"code": "MISSING_TITLE", "message": "title is missing."})
    if not extraction.ingredients:
        errors.append(
            {"code": "MISSING_INGREDIENTS", "message": "ingredients are missing."}
        )
    if not extraction.steps:
        errors.append({"code": "MISSING_STEPS", "message": "steps are missing."})
    if not extraction.servings:
        errors.append({"code": "MISSING_SERVINGS", "message": "servings are missing."})
    if not extraction.cooking_time_minutes:
        errors.append(
            {"code": "MISSING_COOKING_TIME", "message": "cooking time is missing."}
        )
    if extraction.difficulty not in VALID_DIFFICULTIES:
        errors.append(
            {"code": "INVALID_DIFFICULTY", "message": "difficulty is invalid."}
        )
    if not any(label.label_type == "CATEGORY" for label in extraction.labels):
        errors.append({"code": "MISSING_CATEGORY", "message": "category is missing."})
    return errors


def _build_quality_score(
    extraction: RecipeSourceExtraction,
) -> RecipeSourceQualityScore:
    nutrition_confidence = 0.70 if extraction.kcal_per_serving is not None else None
    estimated_fields = []
    if extraction.kcal_per_serving is not None:
        estimated_fields.append("kcal_per_serving")
    if extraction.cooking_time_minutes is not None:
        estimated_fields.append("cooking_time_minutes")
    return RecipeSourceQualityScore(
        completeness_score=_completeness_score(extraction),
        parse_confidence=0.85,
        ingredient_confidence=0.90 if extraction.ingredients else 0.0,
        metadata_confidence=0.80
        if extraction.servings and extraction.cooking_time_minutes
        else 0.0,
        rewrite_confidence=None,
        nutrition_confidence=nutrition_confidence,
        duplicate_score=None,
        estimated_fields=estimated_fields,
        validation_summary=[],
        quality_notes={
            "source": "10000recipe_parser",
        "kcal_policy": "ai_estimated",
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
        extraction.kcal_per_serving is not None,
        any(label.label_type == "CATEGORY" for label in extraction.labels),
    ]
    return round(sum(checks) / len(checks), 2)


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
        and db.query(Recipe)
        .join(RecipeSource, Recipe.source_id == RecipeSource.source_id)
        .filter(RecipeSource.source_url == source.source_url)
        .first()
    )


def _apply_draft(extraction: RecipeSourceExtraction, draft: RecipeTextDraft) -> None:
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


def _delete_existing_extraction(db, source: RecipeSource) -> None:
    if source.extraction is not None:
        db.delete(source.extraction)
        source.extraction = None
        db.flush()


def process_source(
    db,
    source: RecipeSource,
    text_rewriter: RecipeTextRewriter = recipe_text_rewrite_service,
) -> str:
    _delete_existing_extraction(db, source)
    try:
        extraction = build_extraction(source.raw_payload)
    except ExtractionBuildError as exc:
        logger.warning("parse failed (source_id=%d): %s", source.source_id, exc)
        source.parse_status = "INVALID"
        source.review_status = "PENDING"
        source.validation_errors = exc.errors
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return "INVALID"
    except Exception as exc:
        logger.warning("parse failed (source_id=%d): %s", source.source_id, exc)
        source.parse_status = "INVALID"
        source.review_status = "PENDING"
        source.validation_errors = [{"code": "PARSE_ERROR", "message": str(exc)}]
        source.parsed_at = datetime.now(UTC)
        db.commit()
        return "INVALID"

    source.raw_content_hash = extraction.content_hash
    source.parsed_at = datetime.now(UTC)

    if is_duplicate(db, source, extraction):
        source.extraction = extraction
        source.parse_status = "DUPLICATE"
        source.review_status = "PENDING"
        db.commit()
        return "DUPLICATE"

    errors = validate(extraction)
    if extraction.quality_score is not None:
        extraction.quality_score.validation_summary = errors
    if not errors:
        try:
            _apply_draft(extraction, text_rewriter.rewrite(extraction))
            if extraction.quality_score is not None:
                extraction.quality_score.rewrite_confidence = 0.80
            source.extraction_version = EXTRACTION_VERSION
        except Exception as exc:
            logger.warning("rewrite failed (source_id=%d): %s", source.source_id, exc)
            source.parse_status = "INVALID"
            source.validation_errors = [{"code": "REWRITE_ERROR", "message": str(exc)}]
            source.review_status = "PENDING"
            db.commit()
            return "INVALID"

    source.extraction = extraction
    source.validation_errors = errors
    source.parse_status = "REVIEW_REQUIRED" if errors else "PARSED"
    source.review_status = "PENDING"
    db.commit()
    return source.parse_status


def source_query(db, refresh: bool, retry_invalid: bool = False):
    query = (
        db.query(RecipeSource)
        .filter(
            RecipeSource.source_type == SOURCE_TYPE,
            RecipeSource.source_site == SOURCE_SITE,
        )
        .order_by(RecipeSource.source_id)
    )
    if retry_invalid:
        query = query.filter(RecipeSource.parse_status == "INVALID")
    elif not refresh:
        query = query.filter(RecipeSource.parse_status == "NOT_PARSED")
    return query


def _process_one(source_id: int) -> tuple[int, str]:
    db = SessionLocal()
    try:
        source = (
            db.query(RecipeSource)
            .filter(RecipeSource.source_id == source_id)
            .first()
        )
        if not source:
            return source_id, "NOT_FOUND"
        result = process_source(db, source)
        return source_id, result
    except Exception as exc:
        logger.error("worker error source_id=%d: %s", source_id, exc)
        return source_id, "ERROR"
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse 10000recipe recipe_sources")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Rebuild existing 10000recipe extractions instead of only NOT_PARSED rows."
        ),
    )
    parser.add_argument(
        "--retry-invalid",
        action="store_true",
        help="Retry only INVALID sources.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        source_ids = [
            s.source_id
            for s in source_query(
                db,
                refresh=args.refresh,
                retry_invalid=args.retry_invalid,
            )
            .limit(args.limit)
            .all()
        ]
    finally:
        db.close()

    logger.info(
        "starting %d source parses with %d workers",
        len(source_ids),
        args.workers,
    )
    counts: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_process_one, sid): sid for sid in source_ids}
        for future in as_completed(futures):
            source_id, result = future.result()
            counts[result] = counts.get(result, 0) + 1
            logger.info("[%s] source_id=%d", result, source_id)

    logger.info("done: %s", counts)


if __name__ == "__main__":
    main()
