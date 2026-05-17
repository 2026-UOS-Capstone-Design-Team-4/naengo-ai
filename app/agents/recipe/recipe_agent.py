import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.dependencies import RecipeDeps
from app.agents.core.system_prompts import COOKING_ANSWER_PROMPT, RECIPE_AGENT_PROMPT
from app.core import config
from app.services.recipe_retrieval_service import recipe_retrieval_service

logger = logging.getLogger(__name__)

_model = OpenAIChatModel(
    config.MODEL_NAME,
    provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
)

recipe_agent = Agent(
    _model,
    deps_type=RecipeDeps,
    system_prompt=RECIPE_AGENT_PROMPT,
)

cooking_agent = Agent(
    _model,
    system_prompt=COOKING_ANSWER_PROMPT,
)


@recipe_agent.tool
def search_recipes(ctx: RunContext[RecipeDeps], query: str) -> str:
    """사용자의 재료와 요청을 바탕으로 유사 레시피를 최대 3개 검색합니다."""
    if ctx.deps.last_found_recipes:
        titles = ", ".join(
            str(recipe.get("title") or "제목 없음")
            for recipe in ctx.deps.last_found_recipes
        )
        logger.info("레시피 검색: 사전 검색 결과 재사용")
        return f"검색 재료: {query}\n찾은 레시피: {titles}"

    search_query = (
        ctx.deps.search_plan.query_text
        if ctx.deps.search_plan is not None
        else query
    )
    logger.info("레시피 검색: %s", search_query)

    try:
        recipes = recipe_retrieval_service.search_recipes(
            search_query,
            limit=3,
            plan=ctx.deps.search_plan,
        )
        if not recipes:
            return "검색 결과가 없습니다."

        for recipe in recipes:
            ctx.deps.last_found_recipes.append(
                recipe_retrieval_service.recipe_to_payload(recipe)
            )

        titles = ", ".join(recipe.title for recipe in recipes)
        return f"검색 재료: {query}\n찾은 레시피: {titles}"

    except Exception as exc:
        logger.error("레시피 검색 오류: %s", exc)
        return "검색 중 오류가 발생했습니다."
