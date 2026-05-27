from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.core.memory import AgentMemory
from app.agents.intent.intent_models import AnswerStrategy


@dataclass(frozen=True)
class AnswerVerificationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {"passed": self.passed, "issues": self.issues}


class AnswerVerifier:
    def verify(
        self,
        answer: str,
        recipes: list[dict],
        memory: AgentMemory | None,
        *,
        plan: Any | None = None,
        answer_strategy: AnswerStrategy | None = None,
        resolved_recipe_ids: list[int] | None = None,
    ) -> AnswerVerificationResult:
        issues = []
        long_term = memory.long_term if memory is not None else None
        allergies = _unique(
            [
                *(long_term.allergies if long_term is not None else []),
                *_plan_list(plan, "allergies"),
            ]
        )
        avoid_ingredients = _unique(
            [
                *_plan_list(plan, "avoid_ingredients"),
                *_short_term_avoid_ingredients(memory),
                *(long_term.disliked_ingredients if long_term is not None else []),
            ]
        )
        avoid_ingredients = [
            ingredient
            for ingredient in avoid_ingredients
            if ingredient not in allergies
        ]

        for allergy in allergies:
            for recipe in recipes:
                if _recipe_contains_value(recipe, allergy):
                    issues.append(f"recipe_contains_allergy:{allergy}")

        for ingredient in avoid_ingredients:
            for recipe in recipes:
                if _recipe_contains_value(recipe, ingredient):
                    issues.append(f"recipe_contains_avoid_ingredient:{ingredient}")

        for value in [*allergies, *avoid_ingredients]:
            if _answer_claims_avoidance(answer, value) and any(
                _recipe_contains_value(recipe, value) for recipe in recipes
            ):
                issues.append(f"answer_recipe_conflict_avoid_ingredient:{value}")

        if recipes and _answer_says_no_recipes(answer):
            issues.append("answer_payload_mismatch:no_recipes_text_with_payload")

        if _is_safety_sensitive(plan, answer_strategy) and _answer_is_too_permissive(
            answer
        ):
            issues.append("safety_answer_too_permissive")

        if resolved_recipe_ids and recipes:
            payload_ids = {
                int(recipe.get("id")) for recipe in recipes if recipe.get("id")
            }
            missing = [
                recipe_id
                for recipe_id in resolved_recipe_ids
                if recipe_id not in payload_ids
            ]
            if missing:
                issues.append(f"resolved_recipe_not_in_payload:{missing[0]}")

        return AnswerVerificationResult(passed=not issues, issues=issues)


def _contains_value(text: str, value: str) -> bool:
    normalized_text = "".join(text.lower().split())
    normalized_value = "".join(value.lower().split())
    return bool(normalized_value and normalized_value in normalized_text)


def _recipe_contains_value(recipe: dict, value: str) -> bool:
    haystacks = [
        str(recipe.get("title") or ""),
        str(recipe.get("summary") or ""),
        str(recipe.get("description") or ""),
    ]
    ingredients = recipe.get("ingredients")
    if isinstance(ingredients, list):
        haystacks.extend(str(item) for item in ingredients)
    return any(_contains_value(text, value) for text in haystacks)


def _plan_list(plan: Any | None, field: str) -> list[str]:
    if plan is None:
        return []
    value = plan.get(field) if isinstance(plan, dict) else getattr(plan, field, None)
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _short_term_avoid_ingredients(memory: AgentMemory | None) -> list[str]:
    if memory is None:
        return []
    value = memory.short_term.current_constraints.get("avoid_ingredients")
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _answer_claims_avoidance(answer: str, value: str) -> bool:
    patterns = [
        f"{value}는 피",
        f"{value}은 피",
        f"{value}를 피",
        f"{value}을 피",
        f"{value} 없이",
        f"{value} 빼",
        f"{value} 제외",
    ]
    return any(pattern in answer for pattern in patterns)


def _answer_says_no_recipes(answer: str) -> bool:
    return any(
        marker in answer
        for marker in [
            "검색 결과가 없습니다",
            "찾지 못했",
            "추천할 레시피가 없",
            "레시피가 없",
        ]
    )


def _is_safety_sensitive(
    plan: Any | None,
    answer_strategy: AnswerStrategy | None,
) -> bool:
    return bool(
        answer_strategy == AnswerStrategy.SAFETY_COOKING_QA
        or (plan is not None and getattr(plan, "safety_sensitive", False))
    )


def _answer_is_too_permissive(answer: str) -> bool:
    permissive = ("먹어도 돼요", "먹어도 됩니다", "괜찮아요", "문제없어요")
    caution = ("확실하지", "위험", "폐기", "권하지", "주의", "온도", "재가열")
    return any(text in answer for text in permissive) and not any(
        text in answer for text in caution
    )


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


answer_verifier = AnswerVerifier()
