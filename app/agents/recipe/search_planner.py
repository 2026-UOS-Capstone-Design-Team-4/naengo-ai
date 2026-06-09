import base64
import re

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryContent, ImageUrl, ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.system_prompts import SEARCH_PLANNER_PROMPT
from app.agents.intent.intent_models import AnswerStrategy, RecipeFindSubIntent
from app.core import config

_DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _to_image_content(image: str) -> BinaryContent | ImageUrl:
    m = _DATA_URL_RE.match(image)
    if m:
        return BinaryContent(data=base64.b64decode(m.group(2)), media_type=m.group(1))
    return ImageUrl(url=image)


class SearchPlan(BaseModel):
    query_text: str
    sub_intent: RecipeFindSubIntent = RecipeFindSubIntent.BY_INGREDIENTS
    target_dish_name: str | None = None
    available_ingredients: list[str] = []
    main_ingredients: list[str] = []
    required_ingredients: list[str] = []
    avoid_ingredients: list[str] = []
    cooking_time_max: int | None = None
    difficulty: str | None = None
    cooking_skill: str | None = None
    preferred_cooking_time_minutes: int | None = None
    cuisine_type: str | None = None
    dish_type: str | None = None
    cooking_method: str | None = None
    taste_keywords: list[str] = []
    diet_keywords: list[str] = []
    allergies: list[str] = []
    preferred_ingredients: list[str] = []
    disliked_ingredients: list[str] = []
    servings: int | None = None
    retrieval_required: bool = True
    clarification_required: bool = False
    clarification_question: str | None = None
    answer_strategy: AnswerStrategy = AnswerStrategy.RECIPE_RECOMMENDATION


class RecipeSearchPlanner:
    def __init__(self) -> None:
        model = OpenAIChatModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=SearchPlan,
            system_prompt=SEARCH_PLANNER_PROMPT,
        )

    async def plan(
        self,
        message: str,
        history: list[ModelMessage],
        memory_context: str | None = None,
        image: str | None = None,
    ) -> SearchPlan:
        text = message
        if memory_context:
            text = "\n\n".join([memory_context, f"[요청]\n{message}"])

        prompt = [text, _to_image_content(image)] if image else text
        result = await self._agent.run(prompt, message_history=history)
        return result.output


recipe_search_planner = RecipeSearchPlanner()
