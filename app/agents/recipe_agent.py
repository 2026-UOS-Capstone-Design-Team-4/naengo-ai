# 레시피 생성 및 추천 로직 에이전트
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.system_prompts import RECIPE_AGENT_PROMPT
from app.core import config

# 1. 모델 설정 (OpenAI 호환 모델)
my_provider = OpenAIProvider(
    base_url=config.BASE_URL,
    api_key=config.API_KEY,
)

my_model = OpenAIChatModel(
    model_name=config.MODEL_NAME,
    provider=my_provider,
)

# 2. 에이전트 생성
# 범용 에이전트 예시 (기존 main.py 로직)
recipe_agent = Agent(
    my_model,
    system_prompt=RECIPE_AGENT_PROMPT,
)
