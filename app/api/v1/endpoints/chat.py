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
    summary="스트리밍 대화",
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
    - **클라이언트 처리**: 프론트엔드에서는 `ReadableStream` 등을 사용하여
      순차적으로 데이터를 조립해야 합니다.
    - **히스토리**: 기존 대화 내역(`history`)을 포함하면 문맥을 유지하며 답변합니다.
    """
    try:
        message_history = (
            convert_history_to_messages(request.history) if request.history else None
        )

        async def event_generator():
            async with recipe_agent.run_stream(
                request.prompt, message_history=message_history
            ) as result:
                async for chunk in result.stream_text(delta=True):
                    yield chunk

        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=ChatResponse, summary="일반 대화 (JSON)")
async def chat(request: ChatRequest):
    """
    PydanticAI를 이용한 일반 대화 엔드포인트입니다.
    전체 답변이 완료된 후 JSON 형식으로 반환합니다.
    """
    try:
        message_history = (
            convert_history_to_messages(request.history) if request.history else None
        )

        result = await recipe_agent.run(request.prompt, message_history=message_history)
        return ChatResponse(message=result.data)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
