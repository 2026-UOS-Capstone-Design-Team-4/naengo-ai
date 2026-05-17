from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.system_prompts import SEARCH_PLANNER_PROMPT
from app.core import config


class SearchPlan(BaseModel):
    query_text: str
    target_dish_name: str | None = None
    available_ingredients: list[str] = []
    main_ingredients: list[str] = []
    required_ingredients: list[str] = []
    avoid_ingredients: list[str] = []
    cooking_time_max: int | None = None
    difficulty: str | None = None
    cuisine_type: str | None = None
    dish_type: str | None = None
    cooking_method: str | None = None
    taste_keywords: list[str] = []
    diet_keywords: list[str] = []
    servings: int | None = None


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
        user_profile_context: str | None = None,
    ) -> SearchPlan:
        prompt = message
        if user_profile_context:
            prompt = f"[사용자 프로필]\n{user_profile_context}\n\n[요청]\n{message}"

        result = await self._agent.run(prompt, message_history=history)
        return result.output


recipe_search_planner = RecipeSearchPlanner()
