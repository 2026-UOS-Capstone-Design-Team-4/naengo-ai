from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.system_prompts import COOKING_QA_PLANNER_PROMPT
from app.agents.intent.intent_models import AnswerStrategy, CookingQASubIntent
from app.core import config

ReferenceType = Literal[
    "CURRENT_RECIPE",
    "PREVIOUS_RECOMMENDATION_INDEX",
    "EXPLICIT_RECIPE_ID",
    "EXPLICIT_TITLE",
    "UNKNOWN",
]


class ReferencedRecipe(BaseModel):
    reference_type: ReferenceType = "UNKNOWN"
    recipe_id: int | None = None
    recommendation_index: int | None = None
    title: str | None = None
    confidence: float = 0.0


class CookingQAPlan(BaseModel):
    sub_intent: CookingQASubIntent = CookingQASubIntent.GENERAL
    question_type: Literal[
        "RECIPE_REFERENCE",
        "STEP_HELP",
        "INGREDIENT_SUBSTITUTION",
        "TECHNIQUE",
        "STORAGE",
        "SAFETY",
        "NUTRITION",
        "GENERAL",
    ] = "GENERAL"
    referenced_recipe: ReferencedRecipe | None = None
    referenced_step_no: int | None = None
    referenced_ingredients: list[str] = []
    target_dish_name: str | None = None
    needs_recipe_context: bool = False
    needs_retrieval: bool = False
    needs_live_research: bool = False
    safety_sensitive: bool = False
    rewritten_question: str
    clarification_required: bool = False
    clarification_question: str | None = None
    answer_strategy: AnswerStrategy = AnswerStrategy.GENERAL_COOKING_QA


class CookingQAPlanner:
    def __init__(self) -> None:
        model = OpenAIChatModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=CookingQAPlan,
            system_prompt=COOKING_QA_PLANNER_PROMPT,
        )

    async def plan(
        self,
        message: str,
        history: list[ModelMessage],
        memory_context: str | None = None,
    ) -> CookingQAPlan:
        prompt = message
        if memory_context:
            prompt = "\n\n".join([memory_context, f"[요청]\n{message}"])
        result = await self._agent.run(prompt, message_history=history)
        return result.output


cooking_qa_planner = CookingQAPlanner()
