from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.evals.dataset import AgentEvalCase, EvalOutput
from app.services.recipe_retrieval_service import recipe_retrieval_service


@dataclass
class RetrievalOutputProvider:
    limit: int = 3

    def __call__(self, case: AgentEvalCase) -> EvalOutput:
        started = perf_counter()
        recipes = recipe_retrieval_service.search_recipes(
            case.inputs.message,
            limit=self.limit,
        )
        recipe_ids = [int(recipe.recipe_id) for recipe in recipes]
        return EvalOutput(
            primary_task=case.expected.primary_task,
            sub_intent=case.expected.sub_intent,
            answer_strategy=case.expected.answer_strategy,
            selected_agent=case.expected.selected_agent,
            retrieval_used=True,
            recipe_ids=recipe_ids,
            latency_ms=(perf_counter() - started) * 1000,
        )
