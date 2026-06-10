from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.agents.core.memory import AgentMemory, LongTermMemory, ShortTermMemory
from app.models.user import UserProfile
from app.services.chat_service import ChatService
from app.services.personalization_taxonomy import canonicalize_profile_values


class ConversationMemoryBuilder:
    def build(
        self,
        db: Session | None,
        user_id: int | None,
        room_id: int | None,
        chat_service: ChatService | None,
        prompt: str,
    ) -> AgentMemory:
        return AgentMemory(
            short_term=self._build_short_term(room_id, chat_service, prompt),
            long_term=self._build_long_term(db, user_id),
        )

    def _build_short_term(
        self,
        room_id: int | None,
        chat_service: ChatService | None,
        prompt: str,
    ) -> ShortTermMemory:
        recent_recipe_ids: list[int] = []
        if (
            room_id is not None
            and chat_service is not None
            and hasattr(chat_service, "load_recent_recipe_refs")
        ):
            recent_recipe_ids = chat_service.load_recent_recipe_refs(room_id, limit=5)

        return ShortTermMemory(
            recent_recipe_ids=recent_recipe_ids,
            recent_ingredients=_extract_recent_ingredients(prompt),
            current_constraints=_extract_current_constraints(prompt),
        )

    def _build_long_term(
        self,
        db: Session | None,
        user_id: int | None,
    ) -> LongTermMemory | None:
        if db is None or user_id is None:
            return None

        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if profile is None:
            return None

        return LongTermMemory(
            allergies=canonicalize_profile_values("allergies", profile.allergies),
            dietary_restrictions=canonicalize_profile_values(
                "dietary_restrictions",
                profile.dietary_restrictions,
            ),
            preferred_ingredients=canonicalize_profile_values(
                "preferred_ingredients",
                profile.preferred_ingredients,
            ),
            disliked_ingredients=canonicalize_profile_values(
                "disliked_ingredients",
                profile.disliked_ingredients,
            ),
            preferred_categories=canonicalize_profile_values(
                "preferred_categories",
                profile.preferred_categories,
            ),
            taste_keywords=canonicalize_profile_values(
                "taste_keywords",
                profile.taste_keywords,
            ),
            cooking_skill=profile.cooking_skill,
            preferred_cooking_time_minutes=profile.preferred_cooking_time_minutes,
            serving_size=float(profile.serving_size) if profile.serving_size else None,
        )


def _list_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _extract_recent_ingredients(prompt: str) -> list[str]:
    text = _normalize_prompt(prompt)
    match = re.search(
        r"(.{1,80}?)(?:있(?:어|어요|고|는데|음)?|가지고|남았)",
        text,
    )
    if match is None:
        return []
    segment = match.group(1)
    segment = re.sub(
        r"(냉장고에|집에|재료는|재료가|재료|나는|저는|나|저|오늘은|오늘|"
        r"이번엔|이번에는)",
        " ",
        segment,
    )
    return _ingredient_list_from_text(segment)


def _extract_current_constraints(prompt: str) -> dict[str, Any]:
    avoid_ingredients = _extract_avoid_ingredients(prompt)
    if not avoid_ingredients:
        return {}
    return {"avoid_ingredients": avoid_ingredients}


def _extract_avoid_ingredients(prompt: str) -> list[str]:
    text = _normalize_prompt(prompt)
    values: list[str] = []
    patterns = [
        r"([가-힣A-Za-z0-9\s,]+?)\s*(?:빼줘|빼고|제외해줘|제외하고|넣지\s*마)",
        r"([가-힣A-Za-z0-9\s,]+?)\s*없이",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            phrase = _avoid_phrase(match.group(1))
            for ingredient in _ingredient_list_from_text(phrase):
                if ingredient not in values:
                    values.append(ingredient)
    return values


def _avoid_phrase(text: str) -> str:
    return re.sub(
        r"^.*(?:있고|있어|있어요|있는데|있음|가지고|남았고|남았는데)\s*",
        "",
        text,
    )


def _ingredient_list_from_text(text: str) -> list[str]:
    cleaned = re.sub(
        r"(오늘은|오늘|이번엔|이번에는|그건|그거|그리고|근데|혹시|좀|"
        r"제발|별로고|별로|추천|해줘|요리|만들|먹|있)",
        " ",
        text,
    )
    cleaned = re.sub(r"(이랑|랑|하고|와|과|및|/|\+|,)", ",", cleaned)
    values: list[str] = []
    for raw in re.split(r"[,\s]+", cleaned):
        value = raw.strip(" .!?~요은는이가을를도만")
        if len(value) < 2:
            continue
        if value in {"냉장고", "재료", "오늘", "이번", "별로"}:
            continue
        if value not in values:
            values.append(value)
    return values[:8]


def _normalize_prompt(prompt: str) -> str:
    return " ".join(str(prompt).strip().split())


conversation_memory_builder = ConversationMemoryBuilder()
