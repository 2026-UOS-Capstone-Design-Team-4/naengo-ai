import json
import logging

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
from app.schemas.chat import ChatContent, ChatRequest, ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)


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
    "/stream",
    summary="레시피 추천 대화 (스트리밍)",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "실시간 텍스트 스트림 응답 (Chunk 단위)",
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "description": "텍스트 조각",
                        "example": "안녕... 하세... 요! 무엇을... 도와... 드릴까요?",
                    }
                }
            },
        }
    },
)
async def chat_stream(request: ChatRequest):
    """
    PydanticAI를 이용한 스트리밍 대화 엔드포인트입니다.
    - **응답 방식**: `text/plain` 타입으로 텍스트 조각(chunk)을 실시간으로 전송합니다.
    - **레시피 데이터**: 답변 끝에 `[RECIPE_DATA: [...]]` 형식으로 JSON이 추가됩니다.
    - **히스토리**: `history`를 포함하면 문맥을 유지하며 답변합니다.
    - **클라이언트**: `ReadableStream` 등으로 순차적으로 데이터를 조립해야 합니다.
    """
    try:
        message_history = (
            convert_history_to_messages(request.history) if request.history else None
        )

        # 1. 의존성 객체 생성 (레시피 정보를 담을 바구니)
        deps = RecipeDeps()

        async def event_generator():
            # 2. 스트리밍 실행 (deps 전달)
            async with recipe_agent.run_stream(
                request.prompt, message_history=message_history, deps=deps
            ) as result:
                async for chunk in result.stream_text(delta=True):
                    yield chunk

            # 3. 답변이 모두 끝난 후, 검색된 레시피들이 있다면 리스트 형태로 주입!
            if deps.last_found_recipes:
                # 중복 제거 (여러 번 호출될 경우를 대비)
                unique_recipes = {r["id"]: r for r in deps.last_found_recipes}.values()
                json_data = json.dumps(list(unique_recipes), ensure_ascii=False)

                logger.info(
                    f"💾 [Stream] {len(unique_recipes)}개의 레시피 데이터를 스트림 끝에 주입합니다."
                )
                yield f"\n\n[RECIPE_DATA: {json_data}]"

        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "",
    summary="레시피 추천 대화 (JSON 응답)",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "AI 응답 텍스트와 추천 레시피 목록",
            "content": {
                "application/json": {
                    "example": {
                        "message": "냉장고에 계란이 있으시군요! 추천 레시피를 알려드릴게요.",
                        "recipes": [
                            {"id": 1, "title": "계란비빔밥", "description": "간단하고 맛있는 계란비빔밥"},
                        ],
                    }
                }
            },
        }
    },
)
async def chat(request: ChatRequest):
    """
    PydanticAI를 이용한 일반 대화 엔드포인트입니다.
    - **응답 방식**: AI 응답 텍스트와 추천 레시피 목록을 JSON으로 반환합니다.
    - **레시피 데이터**: 레시피 검색 결과가 없으면 `recipes`는 `null`로 반환됩니다.
    - **히스토리**: `history`를 포함하면 문맥을 유지하며 답변합니다.
    """
    try:
        message_history = (
            convert_history_to_messages(request.history) if request.history else None
        )

        deps = RecipeDeps()

        result = await recipe_agent.run(
            request.prompt, message_history=message_history, deps=deps
        )

        unique_recipes = (
            list({r["id"]: r for r in deps.last_found_recipes}.values())
            if deps.last_found_recipes
            else None
        )

        return ChatResponse(message=result.output, recipes=unique_recipes)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
