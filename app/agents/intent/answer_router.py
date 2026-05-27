from dataclasses import dataclass
from typing import Any

from app.agents.core.run_context import AgentRunContext
from app.agents.intent.intent_models import (
    AnswerStrategy,
    CookingQASubIntent,
    PrimaryTask,
)
from app.agents.recipe.recipe_agent import (
    cooking_agent,
    ingredient_substitution_agent,
    recipe_agent,
    recipe_context_qa_agent,
    safety_cooking_agent,
    smalltalk_agent,
)


@dataclass(frozen=True)
class AnswerAgentDecision:
    agent: Any | None
    strategy: AnswerStrategy
    selected_agent: str | None = None


class DomainAnswerRouter:
    def decide(self, context: AgentRunContext) -> AnswerAgentDecision:
        strategy = context.answer_strategy

        if context.primary_task == PrimaryTask.SMALLTALK:
            return AnswerAgentDecision(smalltalk_agent, strategy, "smalltalk_agent")

        if context.primary_task == PrimaryTask.RECIPE_FIND:
            return AnswerAgentDecision(recipe_agent, strategy, "recipe_agent")

        if context.primary_task == PrimaryTask.COOKING_QA:
            return self._decide_cooking_qa(context)

        return AnswerAgentDecision(None, strategy, None)

    def _decide_cooking_qa(self, context: AgentRunContext) -> AnswerAgentDecision:
        strategy = context.answer_strategy
        sub_intent = getattr(context.domain_plan, "sub_intent", None)

        if sub_intent == CookingQASubIntent.RECIPE_CONTEXT:
            return AnswerAgentDecision(
                recipe_context_qa_agent,
                strategy,
                "recipe_context_qa_agent",
            )
        if sub_intent == CookingQASubIntent.INGREDIENT_SUBSTITUTION:
            return AnswerAgentDecision(
                ingredient_substitution_agent,
                strategy,
                "ingredient_substitution_agent",
            )
        if sub_intent == CookingQASubIntent.SAFETY:
            return AnswerAgentDecision(
                safety_cooking_agent,
                strategy,
                "safety_cooking_agent",
            )
        return AnswerAgentDecision(cooking_agent, strategy, "general_cooking_qa_agent")


domain_answer_router = DomainAnswerRouter()
