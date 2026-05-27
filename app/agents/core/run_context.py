from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.core.conversation_state import ConversationState
from app.agents.core.memory import AgentMemory
from app.agents.intent.intent_models import (
    AnswerStrategy,
    MainIntentResult,
    PrimaryTask,
)


@dataclass
class AgentRunContext:
    prompt: str
    user_id: int | None
    room_id: int | None
    main_intent: MainIntentResult
    answer_strategy: AnswerStrategy
    memory: AgentMemory = field(default_factory=AgentMemory)
    conversation_state: ConversationState | None = None
    live_research_result: Any | None = None
    domain_plan: Any | None = None
    resolved_context: dict[str, Any] = field(default_factory=dict)
    retrieved_recipes: list[dict] = field(default_factory=list)
    evidence_pack: Any | None = None
    verification: dict[str, Any] | None = None

    @property
    def primary_task(self) -> PrimaryTask:
        return self.main_intent.primary_task
