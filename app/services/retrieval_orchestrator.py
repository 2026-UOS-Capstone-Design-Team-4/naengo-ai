from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.core.evidence_pack import EvidencePack, EvidenceRecipe
from app.agents.core.memory import AgentMemory
from app.services.recipe_retrieval_service import recipe_retrieval_service


@dataclass(frozen=True)
class RetrievalOrchestratorResult:
    recipe_payloads: list[dict] = field(default_factory=list)
    evidence_pack: EvidencePack = field(default_factory=EvidencePack)


class RetrievalOrchestrator:
    def __init__(self, retrieval_service=recipe_retrieval_service) -> None:
        self.retrieval_service = retrieval_service

    def search(
        self,
        query: str,
        limit: int = 3,
        plan: Any | None = None,
        memory: AgentMemory | None = None,
        liked_ids: set[int] | None = None,
        scrapped_ids: set[int] | None = None,
    ) -> RetrievalOrchestratorResult:
        recipes = self.retrieval_service.search_recipes(
            query,
            limit=limit,
            plan=plan,
        )
        payloads = [
            self.retrieval_service.recipe_to_payload(
                recipe,
                liked_ids=liked_ids,
                scrapped_ids=scrapped_ids,
            )
            for recipe in recipes
        ]
        payloads = _filter_payloads_for_memory(payloads, memory)
        payloads = _filter_payloads_for_hard_diets(payloads, plan)
        evidence_pack = EvidencePack(
            recipes=[
                _evidence_recipe(payload, plan=plan, memory=memory)
                for payload in payloads
            ],
            constraints=_constraints(plan=plan, memory=memory),
        )
        return RetrievalOrchestratorResult(
            recipe_payloads=payloads,
            evidence_pack=evidence_pack,
        )


def _evidence_recipe(
    payload: dict,
    plan: Any | None,
    memory: AgentMemory | None,
) -> EvidenceRecipe:
    return EvidenceRecipe(
        recipe_id=int(payload.get("id") or 0),
        title=str(payload.get("title") or "제목 없음"),
        why_matched=_why_matched(payload, plan),
        risk_flags=_risk_flags(payload, memory),
        missing_ingredients=_missing_ingredients(payload, plan),
        time_minutes=payload.get("cooking_time_minutes"),
        difficulty=payload.get("difficulty"),
    )


def _why_matched(payload: dict, plan: Any | None) -> list[str]:
    matched: list[str] = []
    recipe_text = _payload_text(payload)
    for value in [
        *_plan_list(plan, "main_ingredients"),
        *_plan_list(plan, "available_ingredients"),
        *_plan_list(plan, "preferred_ingredients"),
    ]:
        if _contains(recipe_text, value) and value not in matched:
            matched.append(value)
    target_dish_name = _plan_value(plan, "target_dish_name")
    title = str(payload.get("title") or "")
    if target_dish_name and _contains(title, str(target_dish_name)):
        matched.append(str(target_dish_name))
    cooking_time_max = _plan_value(plan, "cooking_time_max")
    if cooking_time_max and payload.get("cooking_time_minutes"):
        try:
            if int(payload["cooking_time_minutes"]) <= int(cooking_time_max):
                matched.append(f"{int(cooking_time_max)}분 이내")
        except (TypeError, ValueError):
            pass
    for keyword in _plan_list(plan, "diet_keywords"):
        if keyword in _payload_list(payload, "_diet_keywords"):
            matched.append(f"식단:{keyword}")
    for keyword in _plan_list(plan, "taste_keywords"):
        if keyword in _payload_list(payload, "_taste_keywords"):
            matched.append(f"맛:{keyword}")
    for category in _plan_list(plan, "preferred_categories"):
        categories = [
            *_payload_list(payload, "_category_labels"),
            *_payload_list(payload, "category"),
        ]
        if category in categories:
            matched.append(f"카테고리:{category}")
    skill = _plan_value(plan, "cooking_skill")
    if skill and skill == payload.get("difficulty"):
        matched.append(f"난이도:{skill}")
    preferred_time = _plan_value(plan, "preferred_cooking_time_minutes")
    if preferred_time and payload.get("cooking_time_minutes"):
        try:
            if int(payload["cooking_time_minutes"]) <= int(preferred_time):
                matched.append(f"선호시간:{int(preferred_time)}분")
        except (TypeError, ValueError):
            pass
    servings = _plan_value(plan, "servings")
    if servings and payload.get("servings"):
        try:
            if float(payload["servings"]) == float(servings):
                matched.append(f"인분:{float(servings):g}")
        except (TypeError, ValueError):
            pass
    return matched


def _risk_flags(payload: dict, memory: AgentMemory | None) -> list[str]:
    long = memory.long_term if memory is not None else None
    allergies = long.allergies if long is not None else []
    recipe_text = _payload_text(payload)
    return [
        f"contains_allergy:{allergy}"
        for allergy in allergies
        if _contains(recipe_text, allergy)
    ]


def _missing_ingredients(payload: dict, plan: Any | None) -> list[str]:
    recipe_text = _payload_text(payload)
    available = set(_plan_list(plan, "available_ingredients"))
    required = _plan_list(plan, "required_ingredients")
    return [
        ingredient
        for ingredient in required
        if ingredient not in available and not _contains(recipe_text, ingredient)
    ]


def _constraints(plan: Any | None, memory: AgentMemory | None) -> dict[str, Any]:
    constraints: dict[str, Any] = {}
    avoid = [
        *_plan_list(plan, "avoid_ingredients"),
        *_plan_list(plan, "allergies"),
    ]
    long = memory.long_term if memory is not None else None
    if long is not None:
        avoid.extend(long.allergies)
        constraints["disliked_ingredients"] = long.disliked_ingredients
        constraints["diet_preferences"] = long.dietary_restrictions
        constraints["taste_preferences"] = long.taste_keywords
        constraints["preferred_categories"] = long.preferred_categories
    hard_diets = _plan_list(plan, "hard_diet_keywords")
    if hard_diets:
        constraints["required_diet_keywords"] = hard_diets
    if avoid:
        constraints["avoid_ingredients"] = _unique(avoid)
    cooking_time_max = _plan_value(plan, "cooking_time_max")
    if cooking_time_max:
        constraints["max_time_minutes"] = cooking_time_max
    return constraints


def _filter_payloads_for_memory(
    payloads: list[dict],
    memory: AgentMemory | None,
) -> list[dict]:
    long = memory.long_term if memory is not None else None
    allergies = long.allergies if long is not None else []
    if not allergies:
        return payloads
    return [
        payload
        for payload in payloads
        if not any(_contains(_payload_text(payload), allergy) for allergy in allergies)
    ]


def _filter_payloads_for_hard_diets(
    payloads: list[dict],
    plan: Any | None,
) -> list[dict]:
    required = _plan_list(plan, "hard_diet_keywords")
    if not required:
        return payloads
    return [
        payload
        for payload in payloads
        if all(
            keyword in _payload_list(payload, "_diet_keywords")
            for keyword in required
        )
    ]


def _payload_text(payload: dict) -> str:
    parts = [
        str(payload.get("title") or ""),
        str(payload.get("summary") or ""),
        str(payload.get("description") or ""),
    ]
    ingredients = payload.get("ingredients")
    if isinstance(ingredients, list):
        parts.extend(str(item) for item in ingredients)
    return " ".join(parts)


def _payload_list(payload: dict, field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _contains(text: str, value: str) -> bool:
    normalized_text = "".join(text.lower().split())
    normalized_value = "".join(str(value).lower().split())
    return bool(normalized_value and normalized_value in normalized_text)


def _plan_value(plan: Any | None, field: str) -> Any:
    if plan is None:
        return None
    if isinstance(plan, dict):
        return plan.get(field)
    return getattr(plan, field, None)


def _plan_list(plan: Any | None, field: str) -> list[str]:
    value = _plan_value(plan, field)
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


retrieval_orchestrator = RetrievalOrchestrator()
