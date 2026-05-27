from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.cooking_qa.planner import CookingQAPlan
    from app.agents.core.memory import AgentMemory
    from app.agents.core.run_context import AgentRunContext
    from app.agents.intent.intent_models import AnswerStrategy, MainIntentResult
    from app.agents.recipe.search_planner import SearchPlan


@dataclass
class RecipeDeps:
    last_found_recipes: list[dict] = field(default_factory=list)
    search_plan: SearchPlan | None = None
    cooking_qa_plan: CookingQAPlan | None = None
    main_intent: MainIntentResult | None = None
    run_context: AgentRunContext | None = None
    memory: AgentMemory | None = None
    answer_strategy: AnswerStrategy | None = None
    retrieval_allowed: bool = True
    resolved_recipe_ids: list[int] = field(default_factory=list)
    liked_ids: set[int] | None = None
    scrapped_ids: set[int] | None = None
