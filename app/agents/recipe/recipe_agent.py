from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.dependencies import RecipeDeps
from app.agents.core.system_prompts import (
    ANSWER_REVISION_PROMPT,
    COOKING_ANSWER_PROMPT,
    INGREDIENT_SUBSTITUTION_PROMPT,
    RECIPE_AGENT_PROMPT,
    RECIPE_CONTEXT_QA_PROMPT,
    SAFETY_COOKING_PROMPT,
    SMALLTALK_AGENT_PROMPT,
)
from app.core import config

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

recipe_context_qa_agent = Agent(
    _model,
    system_prompt=RECIPE_CONTEXT_QA_PROMPT,
)

ingredient_substitution_agent = Agent(
    _model,
    system_prompt=INGREDIENT_SUBSTITUTION_PROMPT,
)

safety_cooking_agent = Agent(
    _model,
    system_prompt=SAFETY_COOKING_PROMPT,
)

smalltalk_agent = Agent(
    _model,
    system_prompt=SMALLTALK_AGENT_PROMPT,
)

answer_revision_agent = Agent(
    _model,
    system_prompt=ANSWER_REVISION_PROMPT,
)
