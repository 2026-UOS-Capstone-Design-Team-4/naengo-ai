from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core import config

_SEARCH_PLANNER_SYSTEM_PROMPT = """
너는 사용자의 요리 관련 요청을 레시피 검색에 최적화된 쿼리로 변환하는 전문가야.

사용자의 메시지, 대화 이력, 프로필 정보를 종합해서 검색 계획을 만들어.

## 규칙
- query_text: 레시피 DB 검색에 쓸 풍부하고 구체적인 한국어 쿼리 (예: "김치와 두부로 만드는 간단한 얼큰한 한식")
- available_ingredients: 사용자가 가진 재료 목록
- required_ingredients: 반드시 포함해야 할 재료
- avoid_ingredients: 피해야 할 재료 (알레르기, 싫어하는 것)
- cooking_time_max: 최대 조리 시간(분), 언급 없으면 null
- difficulty: "easy"/"normal"/"hard", 언급 없으면 null
- cuisine_type: 요리 종류 (예: "한식", "중식", "일식", "양식"), 언급 없으면 null
- dish_type: 음식 유형 (예: "국", "볶음", "찜", "반찬", "한 끼"), 언급 없으면 null
- cooking_method: 조리 방법 (예: "끓이기", "볶기", "굽기"), 언급 없으면 null
- taste_keywords: 맛 키워드 (예: "매운", "달콤한", "담백한")
- diet_keywords: 식이 제한 키워드 (예: "비건", "저칼로리")
- servings: 인분 수, 언급 없으면 null
""".strip()


class SearchPlan(BaseModel):
    query_text: str
    available_ingredients: list[str] = []
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
        model = OpenAIModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=SearchPlan,
            system_prompt=_SEARCH_PLANNER_SYSTEM_PROMPT,
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
