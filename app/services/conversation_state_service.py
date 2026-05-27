from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.core.conversation_state import (
    ConversationState,
    LastSuccessfulSearch,
)
from app.agents.core.memory import AgentMemory
from app.services.chat_service import ChatService
from app.services.conversation_memory_service import conversation_memory_builder


class ConversationStateResolver:
    def resolve(
        self,
        db: Session | None,
        user_id: int | None,
        room_id: int | None,
        chat_service: ChatService | None,
        prompt: str,
    ) -> ConversationState:
        memory = conversation_memory_builder.build(
            db=db,
            user_id=user_id,
            room_id=room_id,
            chat_service=chat_service,
            prompt=prompt,
        )
        current_recipe_focus = _current_recipe_focus(memory)
        return ConversationState(
            memory=memory,
            dialogue_phase=_dialogue_phase(memory),
            current_recipe_focus=current_recipe_focus,
            active_constraints=dict(memory.short_term.current_constraints),
            last_successful_search=_last_successful_search(memory),
            rejected_recipe_ids=_rejected_recipe_ids(memory, prompt),
            profile_snapshot=_profile_snapshot(memory),
        )


def _current_recipe_focus(memory: AgentMemory) -> int | None:
    recent_ids = memory.short_term.recent_recipe_ids
    return recent_ids[0] if recent_ids else None


def _last_successful_search(memory: AgentMemory) -> LastSuccessfulSearch:
    return LastSuccessfulSearch(recipe_ids=list(memory.short_term.recent_recipe_ids))


def _dialogue_phase(memory: AgentMemory) -> str:
    if memory.short_term.recent_recipe_ids:
        return "CONTEXT_AVAILABLE"
    return "NEW_REQUEST"


def _rejected_recipe_ids(memory: AgentMemory, prompt: str) -> list[int]:
    if not memory.short_term.recent_recipe_ids:
        return []
    normalized = " ".join(prompt.split())
    reject_markers = ("별로", "싫어", "싫어요", "말고", "다른 거", "다른걸", "다른 것")
    if not any(marker in normalized for marker in reject_markers):
        return []
    return [memory.short_term.recent_recipe_ids[0]]


def _profile_snapshot(memory: AgentMemory) -> dict[str, Any]:
    long = memory.long_term
    if long is None:
        return {}
    snapshot: dict[str, Any] = {}
    if long.allergies:
        snapshot["allergies"] = long.allergies
    if long.dietary_restrictions:
        snapshot["dietary_restrictions"] = long.dietary_restrictions
    if long.preferred_ingredients:
        snapshot["preferred_ingredients"] = long.preferred_ingredients
    if long.disliked_ingredients:
        snapshot["disliked_ingredients"] = long.disliked_ingredients
    if long.cooking_skill:
        snapshot["cooking_skill"] = long.cooking_skill
    if long.preferred_cooking_time_minutes:
        snapshot["preferred_cooking_time_minutes"] = (
            long.preferred_cooking_time_minutes
        )
    if long.serving_size:
        snapshot["serving_size"] = long.serving_size
    return snapshot


conversation_state_resolver = ConversationStateResolver()
