from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.core.memory import AgentMemory


@dataclass(frozen=True)
class LastSuccessfulSearch:
    query_text: str | None = None
    recipe_ids: list[int] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.query_text and not self.recipe_ids


@dataclass(frozen=True)
class ConversationState:
    memory: AgentMemory = field(default_factory=AgentMemory)
    dialogue_phase: str = "NEW_REQUEST"
    current_recipe_focus: int | None = None
    active_constraints: dict[str, Any] = field(default_factory=dict)
    pending_clarification: str | None = None
    last_successful_search: LastSuccessfulSearch = field(
        default_factory=LastSuccessfulSearch
    )
    rejected_recipe_ids: list[int] = field(default_factory=list)
    profile_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str | None:
        lines: list[str] = []
        memory_context = self.memory.to_prompt_context()
        if memory_context:
            lines.append(memory_context)
        lines.append(f"- dialogue_phase: {self.dialogue_phase}")
        if self.current_recipe_focus is not None:
            lines.append(f"- current_recipe_focus: {self.current_recipe_focus}")
        if self.active_constraints:
            lines.append(f"- active_constraints: {self.active_constraints}")
        if self.pending_clarification:
            lines.append(f"- pending_clarification: {self.pending_clarification}")
        if not self.last_successful_search.is_empty():
            lines.append(
                "- last_successful_search: "
                f"{self.last_successful_search.query_text}, "
                f"recipe_ids={self.last_successful_search.recipe_ids}"
            )
        if self.rejected_recipe_ids:
            ids = ", ".join(str(recipe_id) for recipe_id in self.rejected_recipe_ids)
            lines.append(f"- rejected_recipe_ids: {ids}")
        if self.profile_snapshot:
            lines.append(f"- profile_snapshot: {self.profile_snapshot}")
        if not lines:
            return None
        return "[Conversation state]\n" + "\n".join(lines)
