from app.agents.core.run_context import AgentRunContext
from app.agents.intent.answer_router import domain_answer_router
from app.agents.intent.intent_models import (
    AnswerStrategy,
    CookingQASubIntent,
    MainIntentResult,
    PrimaryTask,
)
from app.agents.recipe.recipe_agent import (
    ingredient_substitution_agent,
    recipe_agent,
    recipe_context_qa_agent,
    safety_cooking_agent,
)


class Plan:
    def __init__(self, sub_intent):
        self.sub_intent = sub_intent


def _context(primary_task: PrimaryTask, strategy: AnswerStrategy) -> AgentRunContext:
    return AgentRunContext(
        prompt="test",
        user_id=1,
        room_id=1,
        main_intent=MainIntentResult(
            primary_task=primary_task,
            confidence=0.9,
            reason="test",
        ),
        answer_strategy=strategy,
    )


def test_recipe_find_routes_to_recipe_agent():
    context = _context(
        PrimaryTask.RECIPE_FIND,
        AnswerStrategy.RECIPE_RECOMMENDATION,
    )

    decision = domain_answer_router.decide(context)

    assert decision.agent is recipe_agent
    assert decision.selected_agent == "recipe_agent"


def test_cooking_recipe_context_routes_to_context_agent():
    context = _context(PrimaryTask.COOKING_QA, AnswerStrategy.RECIPE_CONTEXT_QA)
    context.domain_plan = Plan(CookingQASubIntent.RECIPE_CONTEXT)

    decision = domain_answer_router.decide(context)

    assert decision.agent is recipe_context_qa_agent
    assert decision.selected_agent == "recipe_context_qa_agent"


def test_cooking_substitution_routes_to_substitution_agent():
    context = _context(PrimaryTask.COOKING_QA, AnswerStrategy.GENERAL_COOKING_QA)
    context.domain_plan = Plan(CookingQASubIntent.INGREDIENT_SUBSTITUTION)

    decision = domain_answer_router.decide(context)

    assert decision.agent is ingredient_substitution_agent
    assert decision.selected_agent == "ingredient_substitution_agent"


def test_cooking_safety_routes_to_safety_agent():
    context = _context(PrimaryTask.COOKING_QA, AnswerStrategy.SAFETY_COOKING_QA)
    context.domain_plan = Plan(CookingQASubIntent.SAFETY)

    decision = domain_answer_router.decide(context)

    assert decision.agent is safety_cooking_agent
    assert decision.selected_agent == "safety_cooking_agent"
