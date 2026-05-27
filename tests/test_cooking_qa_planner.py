import asyncio

from app.agents.cooking_qa.planner import (
    CookingQAPlan,
    CookingQAPlanner,
    ReferencedRecipe,
)
from app.agents.intent.intent_models import AnswerStrategy, CookingQASubIntent


class FakeAgent:
    def __init__(self, output: CookingQAPlan):
        self.output = output
        self.prompt = None
        self.history = None

    async def run(self, prompt, message_history):
        self.prompt = prompt
        self.history = message_history
        return type("Result", (), {"output": self.output})()


def test_cooking_qa_planner_uses_ai_for_previous_recommendation_reference():
    output = CookingQAPlan(
        sub_intent=CookingQASubIntent.RECIPE_CONTEXT,
        question_type="RECIPE_REFERENCE",
        referenced_recipe=ReferencedRecipe(
            reference_type="PREVIOUS_RECOMMENDATION_INDEX",
            recommendation_index=2,
            confidence=0.9,
        ),
        needs_recipe_context=True,
        rewritten_question="아까 두 번째 거에서 고추장 빼도 돼?",
        answer_strategy=AnswerStrategy.RECIPE_CONTEXT_QA,
    )
    agent = FakeAgent(output)
    planner = CookingQAPlanner()
    planner._agent = agent

    plan = asyncio.run(planner.plan("아까 두 번째 거에서 고추장 빼도 돼?", []))

    assert plan.referenced_recipe is not None
    assert plan.referenced_recipe.recommendation_index == 2
    assert agent.prompt == "아까 두 번째 거에서 고추장 빼도 돼?"


def test_cooking_qa_planner_uses_ai_for_safety_reference():
    output = CookingQAPlan(
        sub_intent=CookingQASubIntent.SAFETY,
        question_type="SAFETY",
        referenced_recipe=ReferencedRecipe(
            reference_type="PREVIOUS_RECOMMENDATION_INDEX",
            recommendation_index=2,
            confidence=0.88,
        ),
        needs_recipe_context=True,
        safety_sensitive=True,
        rewritten_question="아까 두 번째 거가 덜 익었는데 먹어도 돼?",
        answer_strategy=AnswerStrategy.SAFETY_COOKING_QA,
    )
    agent = FakeAgent(output)
    planner = CookingQAPlanner()
    planner._agent = agent

    plan = asyncio.run(planner.plan("아까 두 번째 거가 덜 익었는데 먹어도 돼?", []))

    assert plan.sub_intent == CookingQASubIntent.SAFETY
    assert plan.safety_sensitive is True


def test_cooking_qa_planner_appends_memory_context():
    output = CookingQAPlan(
        sub_intent=CookingQASubIntent.INGREDIENT_SUBSTITUTION,
        question_type="INGREDIENT_SUBSTITUTION",
        rewritten_question="새우 없이 감칠맛 내기",
    )
    agent = FakeAgent(output)
    planner = CookingQAPlanner()
    planner._agent = agent

    plan = asyncio.run(
        planner.plan(
            "새우 대신 감칠맛 내려면 뭐 써?",
            [],
            memory_context="[Agent memory]\n- allergies: 새우",
        )
    )

    assert plan.sub_intent == CookingQASubIntent.INGREDIENT_SUBSTITUTION
    assert agent.prompt == (
        "[Agent memory]\n- allergies: 새우\n\n"
        "[요청]\n새우 대신 감칠맛 내려면 뭐 써?"
    )
