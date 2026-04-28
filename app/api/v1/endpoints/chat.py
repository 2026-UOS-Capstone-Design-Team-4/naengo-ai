import json
import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app.agents.dependencies import RecipeDeps
from app.agents.recipe_agent import recipe_agent
from app.schemas.chat import ChatContent, ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)

IDENTITY_PATTERNS = re.compile(
    r"(넌\s*누구|너\s*누구|네\s*이름|너의\s*이름|당신\s*누구|이름이\s*뭐|어떤\s*ai|무슨\s*ai|어느\s*회사|어떤\s*모델"
    r"|너는\s*뭐|넌\s*뭐|당신은\s*뭐|뭐\s*하는\s*(?:ai|프로그램|봇|것|거)"
    r"|who\s*are\s*you|what\s*are\s*you|your\s*name|what'?s\s*your\s*name"
    r"|gpt|chatgpt|claude|gemini|openai|google|anthropic)",
    re.IGNORECASE,
)
IDENTITY_RESPONSE = "저는 냉고예요! 냉장고 속 재료로 레시피를 추천해드리는 요리 전문가랍니다. 😊 어떤 재료가 있으신가요?"


def convert_history_to_messages(history: list[ChatContent]) -> list[ModelMessage]:
    """프론트엔드 히스토리 형식을 PydanticAI 메시지 형식으로 변환"""
    messages = []
    for item in history:
        content = "".join([p.text for p in item.parts])
        if item.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


@router.post(
    "",
    summary="레시피 추천 대화 (SSE 스트리밍)",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE 형식의 실시간 스트림 응답",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": (
                            "event: message\n"
                            'data: {"content": "김치"}\n\n'
                            "event: message\n"
                            'data: {"content": "와 두부"}\n\n'
                            "event: message\n"
                            'data: {"content": "로 만들 수 있는"}\n\n'
                            "event: message\n"
                            'data: {"content": " 레시피를 찾았어요!"}\n\n'
                            "event: recipes\n"
                            "data: [{"
                            '"id": 1, '
                            '"title": "김치두부찌개", '
                            '"description": "칼칼하고 깊은 맛의 김치두부찌개입니다.", '
                            '"ingredients": [{"name": "김치", "amount": "200", "unit": "g", "type": "메인", "note": "잘 익은 것"}, {"name": "두부", "amount": "1", "unit": "모", "type": "메인", "note": ""}], '
                            '"ingredients_raw": "김치 200g, 두부 1모, 돼지고기 100g, 대파 1대", '
                            '"instructions": ["냄비에 기름을 두르고 김치를 볶는다.", "물을 붓고 끓어오르면 두부를 넣는다.", "10분간 끓인 후 대파를 넣고 마무리한다."], '
                            '"servings": 2.0, '
                            '"cooking_time": 20, '
                            '"calories": 180, '
                            '"difficulty": "easy", '
                            '"category": ["한식", "찌개"], '
                            '"tags": ["얼큰한", "국물요리", "간단"], '
                            '"tips": ["김치는 충분히 익은 것을 사용해야 맛이 좋습니다.", "돼지고기를 추가하면 더 깊은 맛이 납니다."], '
                            '"video_url": "https://youtube.com/watch?v=example", '
                            '"image_url": "https://example.com/image.jpg"'
                            "}]\n\n"
                        ),
                    }
                }
            },
        }
    },
)
async def chat(request: ChatRequest):
    r"""
    PydanticAI를 이용한 SSE 스트리밍 대화 엔드포인트입니다.

    - **응답 방식**: `text/event-stream` 형식으로 이벤트를 실시간으로 전송합니다.
    - **message 이벤트**: AI 텍스트 청크를 `{"content": "..."}` 형식으로 전송합니다.
    - **recipes 이벤트**: 답변 완료 후 검색된 레시피 목록을 `RecipeResponse[]` 형식으로 전송합니다.
    - **히스토리**: `history`를 포함하면 문맥을 유지하며 답변합니다.

    **recipes 이벤트 데이터 구조** (`RecipeResponse[]`):

    | 필드 | 타입 | 설명 |
    |------|------|------|
    | `id` | int | 레시피 ID |
    | `title` | string | 레시피 제목 |
    | `description` | string | 레시피 설명 |
    | `ingredients` | IngredientItem[] | 재료 목록 (name, amount, unit, type, note) |
    | `ingredients_raw` | string | 재료 원문 텍스트 |
    | `instructions` | string[] | 조리 순서 |
    | `servings` | float | 인분 수 |
    | `cooking_time` | int | 조리 시간 (분) |
    | `calories` | int \| null | 칼로리 (kcal) |
    | `difficulty` | string | 난이도 (easy / normal / hard) |
    | `category` | string[] | 카테고리 |
    | `tags` | string[] | 태그 |
    | `tips` | string[] | 조리 팁 |
    | `video_url` | string \| null | YouTube 영상 URL |
    | `image_url` | string \| null | 이미지 URL |
    | `author_type` | string | 작성자 유형 |
    """
    try:
        if IDENTITY_PATTERNS.search(request.prompt):

            async def identity_generator():
                data = json.dumps({"content": IDENTITY_RESPONSE}, ensure_ascii=False)
                yield f"event: message\ndata: {data}\n\n"

            return StreamingResponse(
                identity_generator(), media_type="text/event-stream"
            )

        MAX_HISTORY = 10  # 최근 10개 메시지 (5턴)만 유지
        trimmed_history = request.history[-MAX_HISTORY:] if request.history else None
        message_history = (
            convert_history_to_messages(trimmed_history) if trimmed_history else None
        )

        deps = RecipeDeps()

        async def event_generator():
            async with recipe_agent.run_stream(
                request.prompt, message_history=message_history, deps=deps
            ) as result:
                async for chunk in result.stream_text(delta=True):
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"event: message\ndata: {data}\n\n"

            if deps.last_found_recipes:
                unique_recipes = list(
                    {r["id"]: r for r in deps.last_found_recipes}.values()
                )
                data = json.dumps(unique_recipes, ensure_ascii=False)
                logger.info(
                    f"💾 [Stream] {len(unique_recipes)}개의 레시피 데이터를 전송합니다."
                )
                yield f"event: recipes\ndata: {data}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
