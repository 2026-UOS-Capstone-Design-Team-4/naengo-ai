from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.agents.cooking_qa.planner import CookingQAPlan
from app.agents.core.memory import AgentMemory
from app.models.recipe import Recipe
from app.services.chat_service import ChatService


@dataclass(frozen=True)
class ResolvedAgentContext:
    recipe_ids: list[int] = field(default_factory=list)
    recipes: list[Recipe] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)


class AgentContextResolver:
    def resolve_cooking_qa(
        self,
        plan: CookingQAPlan,
        room_id: int | None,
        chat_service: ChatService | None,
        db: Session | None,
        memory: AgentMemory | None = None,
    ) -> ResolvedAgentContext:
        if not plan.needs_recipe_context or db is None:
            return ResolvedAgentContext()

        recipe = self._resolve_recipe(plan, room_id, chat_service, db, memory)
        if recipe is None:
            return ResolvedAgentContext()

        payload = _recipe_context_payload(recipe)
        if plan.referenced_step_no is not None:
            payload["referenced_step_no"] = plan.referenced_step_no
        if plan.referenced_ingredients:
            payload["referenced_ingredients"] = plan.referenced_ingredients

        return ResolvedAgentContext(
            recipe_ids=[recipe.recipe_id],
            recipes=[recipe],
            payload=payload,
        )

    def _resolve_recipe(
        self,
        plan: CookingQAPlan,
        room_id: int | None,
        chat_service: ChatService | None,
        db: Session,
        memory: AgentMemory | None,
    ) -> Recipe | None:
        ref = plan.referenced_recipe
        if ref is None:
            return None

        if ref.recipe_id is not None:
            return self._load_recipe(db, ref.recipe_id)

        if ref.reference_type in {"CURRENT_RECIPE", "PREVIOUS_RECOMMENDATION_INDEX"}:
            recipe_id = self._resolve_recent_recipe_id(
                plan,
                room_id,
                chat_service,
                memory,
            )
            if recipe_id is not None:
                return self._load_recipe(db, recipe_id)

        if ref.reference_type == "EXPLICIT_TITLE" and ref.title:
            recent_ids = self._recent_recipe_ids(room_id, chat_service, memory)
            return self._find_recipe_by_title(db, ref.title, recent_ids)

        return None

    def _load_recipe(self, db: Session, recipe_id: int) -> Recipe | None:
        return self._base_recipe_query(db).filter(Recipe.recipe_id == recipe_id).first()

    def _find_recipe_by_title(
        self,
        db: Session,
        title: str,
        recent_ids: list[int] | None = None,
    ) -> Recipe | None:
        normalized_title = title.strip()
        if not normalized_title:
            return None

        if recent_ids:
            recent_query = self._base_recipe_query(db).filter(
                Recipe.recipe_id.in_(recent_ids),
            )
            recipe = recent_query.filter(Recipe.title == normalized_title).first()
            if recipe is not None:
                return recipe

            recipe = recent_query.filter(
                Recipe.title.ilike(_contains_pattern(normalized_title), escape="\\"),
            ).first()
            if recipe is not None:
                return recipe

        recipe = (
            self._base_recipe_query(db).filter(Recipe.title == normalized_title).first()
        )
        if recipe is not None:
            return recipe

        return (
            self._base_recipe_query(db)
            .filter(
                Recipe.title.ilike(_contains_pattern(normalized_title), escape="\\")
            )
            .first()
        )

    def _base_recipe_query(self, db: Session):
        return (
            db.query(Recipe)
            .filter(Recipe.is_active.is_(True))
            .options(
                selectinload(Recipe.ingredients_list),
                selectinload(Recipe.steps),
                selectinload(Recipe.labels),
                selectinload(Recipe.nutrition),
                selectinload(Recipe.stats),
            )
        )

    def _resolve_recent_recipe_id(
        self,
        plan: CookingQAPlan,
        room_id: int | None,
        chat_service: ChatService | None,
        memory: AgentMemory | None,
    ) -> int | None:
        ref = plan.referenced_recipe
        if ref is None:
            return None

        recent_ids = self._recent_recipe_ids(room_id, chat_service, memory)
        if not recent_ids:
            return None

        if ref.reference_type == "CURRENT_RECIPE":
            return recent_ids[0]

        if (
            ref.reference_type == "PREVIOUS_RECOMMENDATION_INDEX"
            and ref.recommendation_index is not None
        ):
            index = ref.recommendation_index - 1
            if 0 <= index < len(recent_ids):
                return recent_ids[index]
        return None

    def _resolve_recipe_id(
        self,
        plan: CookingQAPlan,
        room_id: int | None,
        chat_service: ChatService | None,
        memory: AgentMemory | None,
    ) -> int | None:
        ref = plan.referenced_recipe
        if ref is not None and ref.recipe_id is not None:
            return ref.recipe_id
        return self._resolve_recent_recipe_id(plan, room_id, chat_service, memory)

    def _recent_recipe_ids(
        self,
        room_id: int | None,
        chat_service: ChatService | None,
        memory: AgentMemory | None,
    ) -> list[int]:
        recent_ids = memory.short_term.recent_recipe_ids if memory is not None else []
        if (
            not recent_ids
            and room_id is not None
            and chat_service is not None
            and hasattr(chat_service, "load_recent_recipe_refs")
        ):
            recent_ids = chat_service.load_recent_recipe_refs(room_id, limit=5)
        return list(recent_ids)


def _recipe_context_payload(recipe: Recipe) -> dict[str, Any]:
    recipe_payload = {
        "id": recipe.recipe_id,
        "title": recipe.title,
        "summary": _compact_text(getattr(recipe, "summary", None)),
        "description": _compact_text(getattr(recipe, "description", None)),
        "servings": _number(getattr(recipe, "servings", None)),
        "cooking_time_minutes": getattr(recipe, "cooking_time_minutes", None),
        "difficulty": getattr(recipe, "difficulty", None),
        "ingredients": [
            _drop_empty(
                {
                    "group_name": getattr(item, "group_name", None),
                    "name": getattr(item, "name", None),
                    "amount_text": getattr(item, "amount_text", None),
                    "unit": getattr(item, "unit", None),
                    "note": getattr(item, "note", None),
                    "raw_text": getattr(item, "raw_text", None),
                    "is_optional": getattr(item, "is_optional", None),
                }
            )
            for item in getattr(recipe, "ingredients_list", [])
        ],
        "steps": [
            _drop_empty(
                {
                    "step_no": getattr(step, "step_no", None),
                    "instruction": _compact_text(
                        getattr(step, "instruction", None),
                        limit=600,
                    ),
                    "tip": _compact_text(getattr(step, "tip", None), limit=300),
                }
            )
            for step in getattr(recipe, "steps", [])
        ],
        "tips": list(getattr(recipe, "tips", []) or []),
        "warnings": list(getattr(recipe, "warnings", []) or []),
        "nutrition": _nutrition_payload(getattr(recipe, "nutrition", None)),
    }

    return {
        "resolved_recipe_id": recipe.recipe_id,
        "title": recipe.title,
        "recipe": _drop_empty(recipe_payload),
    }


def _nutrition_payload(nutrition: Any | None) -> dict[str, Any]:
    if nutrition is None:
        return {}
    return _drop_empty(
        {
            "serving_weight_grams": _number(
                getattr(nutrition, "serving_weight_grams", None)
            ),
            "kcal_per_serving": _number(getattr(nutrition, "kcal_per_serving", None)),
            "carbohydrate_grams": _number(
                getattr(nutrition, "carbohydrate_grams", None)
            ),
            "protein_grams": _number(getattr(nutrition, "protein_grams", None)),
            "fat_grams": _number(getattr(nutrition, "fat_grams", None)),
            "sodium_milligrams": _number(getattr(nutrition, "sodium_milligrams", None)),
        }
    )


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _compact_text(value: Any | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _number(value: Any | None) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != []
    }


agent_context_resolver = AgentContextResolver()
