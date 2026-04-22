import json
import logging

from openai import OpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.dependencies import RecipeDeps
from app.agents.system_prompts import RECIPE_AGENT_PROMPT
from app.core import config
from app.crud.recipe import search_recipes_by_vector
from app.db.session import SessionLocal
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import Recipe, RecipeStats  # noqa
from app.models.social import Like, Scrap  # noqa
from app.models.user import User  # noqa

# 로그 설정
logger = logging.getLogger(__name__)


# 2. 모델 설정
my_provider = OpenAIProvider(
    base_url=config.BASE_URL,
    api_key=config.API_KEY,
)

my_model = OpenAIChatModel(
    model_name=config.MODEL_NAME,
    provider=my_provider,
)

embedding_client = OpenAI(api_key=config.EMBEDDING_API_KEY)

# 3. 에이전트 생성
recipe_agent = Agent(
    my_model,
    deps_type=RecipeDeps,
    system_prompt=RECIPE_AGENT_PROMPT,
)


# 4. 도구(Tool) 정의 - 여러 개의 레시피 검색 가능하도록 수정
@recipe_agent.tool
def search_recipes(ctx: RunContext[RecipeDeps], query: str) -> str:
    """
    사용자의 재료 정보를 바탕으로 DB에서 가장 유사한 레시피들을 최대 3개까지 검색합니다.
    """
    logger.info(f"💡 [Agent Tool] 에이전트가 레시피 검색 요청: '{query}'")

    db = SessionLocal()
    try:
        # A. 검색어(재료)를 벡터로 변환
        response = embedding_client.embeddings.create(
            input=[query.replace("\n", " ")], model="text-embedding-3-small"
        )
        query_vector = response.data[0].embedding

        # B. DB에서 벡터 유사도 검색 실행 (최대 3개)
        recipes = search_recipes_by_vector(db, query_vector, limit=3)

        if not recipes:
            logger.warning(f"⚠️ [Agent Tool] '{query}'에 대한 검색 결과가 없습니다.")
            return "검색 결과가 없습니다."

        logger.info(f"🍴 [Agent Tool] {len(recipes)}개의 레시피를 찾았습니다!")

        results_for_agent = []
        for r in recipes:
            logger.info(f"   - 제목: {r.title} (ID: {r.recipe_id})")

            recipe_info = {
                "id": r.recipe_id,
                "title": r.title,
                "description": r.description,
                "ingredients_raw": r.ingredients_raw,
                "ingredients": r.ingredients,
                "instructions": r.instructions,
                "video_url": r.video_url,
            }
            # 에이전트에게 줄 리스트에 추가
            results_for_agent.append(recipe_info)
            # [핵심] 나중에 스트림 끝에 주입할 바구니에 추가
            ctx.deps.last_found_recipes.append(recipe_info)

        return json.dumps(results_for_agent, ensure_ascii=False)

    except Exception as e:
        logger.error(f"🚨 [Agent Tool] 에러: {str(e)}")
        return "검색 중 오류 발생"
    finally:
        db.close()
