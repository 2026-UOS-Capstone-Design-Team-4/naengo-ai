from __future__ import annotations

import re
from typing import Any

_TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "allergies": {
        "새우": ("새우", "shrimp", "칵테일새우", "흰다리새우"),
        "게": ("게", "crab"),
        "우유": ("우유", "milk", "유제품", "치즈", "버터", "크림"),
        "달걀": ("달걀", "계란", "egg"),
        "땅콩": ("땅콩", "peanut"),
        "밀": ("밀", "밀가루", "flour", "글루텐"),
        "대두": ("대두", "콩", "두부", "된장", "간장"),
    },
    "dietary_restrictions": {
        "vegan": ("비건", "완전채식", "vegan"),
        "vegetarian": ("채식", "베지테리언", "vegetarian"),
        "low_calorie": ("저칼로리", "다이어트", "low calorie"),
        "low_carb": ("저탄수", "저탄수화물", "저탄고지", "low carb"),
        "high_protein": ("고단백", "단백질", "high protein"),
        "gluten_free": ("글루텐프리", "무글루텐", "gluten free"),
    },
    "taste_keywords": {
        "spicy": (
            "매운",
            "매운맛",
            "매콤",
            "매콤함",
            "얼큰",
            "칼칼",
            "칼칼함",
            "spicy",
        ),
        "savory": (
            "고소",
            "고소함",
            "담백",
            "담백함",
            "감칠맛",
            "구수",
            "savory",
        ),
        "sweet": ("달콤", "달콤함", "달달", "단맛", "sweet"),
        "sour": ("새콤", "새콤함", "신맛", "sour"),
        "salty": ("짭짤", "짭짤함", "짠맛", "salty"),
    },
}

_CATEGORY_ALIASES = {
    "한식": ("한식", "한국 음식"),
    "중식": ("중식", "중국 음식"),
    "일식": ("일식", "일본 음식"),
    "양식": ("양식", "서양 음식"),
    "분식": ("분식",),
}

_INGREDIENT_ALIASES = {
    "달걀": ("달걀", "계란", "egg"),
    "새우": ("새우", "칵테일새우", "흰다리새우", "shrimp"),
    "대파": ("대파", "파"),
}

_LIST_FIELDS = {
    "allergies",
    "dietary_restrictions",
    "preferred_ingredients",
    "disliked_ingredients",
    "preferred_categories",
    "taste_keywords",
}
_SCALAR_FIELDS = {
    "cooking_skill",
    "preferred_cooking_time_minutes",
    "serving_size",
}


def canonicalize_profile_value(field: str, value: Any) -> str | int | float:
    if field in _TAXONOMY:
        text = _clean_text(value)
        for canonical, aliases in _TAXONOMY[field].items():
            if _matches_alias(text, canonical, aliases):
                return canonical
        return text
    if field == "preferred_categories":
        text = _clean_text(value)
        for canonical, aliases in _CATEGORY_ALIASES.items():
            if _matches_alias(text, canonical, aliases):
                return canonical
        return text
    if field in {"preferred_ingredients", "disliked_ingredients"}:
        return canonicalize_ingredient(value)
    if field == "cooking_skill":
        return _canonicalize_skill(value)
    if field == "preferred_cooking_time_minutes":
        return int(float(value))
    if field == "serving_size":
        return float(value)
    return _clean_text(value)


def canonicalize_profile_values(field: str, values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        canonical = str(canonicalize_profile_value(field, value)).strip()
        if canonical and canonical not in result:
            result.append(canonical)
    return result


def canonicalize_ingredient(value: Any) -> str:
    text = _clean_text(value)
    for canonical, aliases in _INGREDIENT_ALIASES.items():
        if _matches_alias(text, canonical, aliases):
            return canonical
    return text


def canonicalize_diet_keywords(values: Any) -> list[str]:
    return canonicalize_profile_values("dietary_restrictions", values)


def canonicalize_taste_keywords(values: Any) -> list[str]:
    return canonicalize_profile_values("taste_keywords", values)


def extract_canonical_diet_keywords(text: str) -> list[str]:
    normalized = _normalize(text)
    result = []
    for canonical, aliases in _TAXONOMY["dietary_restrictions"].items():
        matched_aliases = [
            _normalize(alias)
            for alias in (canonical, *aliases)
            if _normalize(alias) in normalized
        ]
        if matched_aliases and not any(
            _is_negated(normalized, alias) for alias in matched_aliases
        ):
            result.append(canonical)
    return result


def profile_field_is_list(field: str) -> bool:
    return field in _LIST_FIELDS


def profile_field_is_scalar(field: str) -> bool:
    return field in _SCALAR_FIELDS


def canonical_aliases(field: str, value: str) -> tuple[str, ...]:
    aliases = _TAXONOMY.get(field, {}).get(value)
    if aliases is None:
        return (value,)
    return tuple(dict.fromkeys((value, *aliases)))


def _canonicalize_skill(value: Any) -> str:
    text = _normalize(value)
    aliases = {
        "easy": {"easy", "초급", "초보", "입문"},
        "normal": {"normal", "중급", "보통"},
        "hard": {"hard", "고급", "숙련"},
    }
    for canonical, values in aliases.items():
        if text in {_normalize(item) for item in values}:
            return canonical
    return _clean_text(value)


def _matches_alias(text: str, canonical: str, aliases: tuple[str, ...]) -> bool:
    normalized = _normalize(text)
    return normalized in {_normalize(item) for item in (canonical, *aliases)}


def _clean_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def _normalize(value: Any) -> str:
    return re.sub(r"[\s_-]+", "", str(value).strip().lower())


def _is_negated(text: str, alias: str) -> bool:
    position = text.find(alias)
    if position < 0:
        return False
    suffix = text[position + len(alias) : position + len(alias) + 6]
    return any(marker in suffix for marker in ("아니", "말고", "제외", "싫", "안해"))
