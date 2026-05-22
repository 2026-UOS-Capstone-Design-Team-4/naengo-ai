import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.errors import ApiError
from app.api.v1.openapi.guest_chat import GUEST_CHAT_RESPONSES
from app.schemas.guest_chat import GuestChatRequest, history_to_model_messages
from app.services.agent_service import AgentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    summary="게스트 채팅",
    description=(
        "비로그인 사용자를 위한 AI 레시피 추천 채팅입니다.\n\n"
        "대화 기록(`history`)은 클라이언트가 직접 관리하며 요청마다 전달합니다. "
        "서버에는 메시지가 저장되지 않습니다. "
        "`history`는 최대 20개(10턴)까지 허용되며, 초과 시 422를 반환합니다.\n\n"
        "응답은 SSE(text/event-stream)로 스트리밍됩니다. "
        "이벤트 종류: `metadata`, `message`, `recipes`, `done`, `error`\n\n"
        "`done` 이벤트의 `message_id`는 항상 `null`입니다."
    ),
    response_class=StreamingResponse,
    responses=GUEST_CHAT_RESPONSES,
)
async def guest_chat(request: GuestChatRequest):
    try:
        history = history_to_model_messages(request.history)
        agent_service = AgentService()

        return StreamingResponse(
            await agent_service.guest_stream(
                prompt=request.prompt,
                image=request.image,
                history=history,
            ),
            media_type="text/event-stream",
        )

    except ApiError:
        raise
    except Exception as exc:
        logger.error("guest_chat 오류: %s", exc)
        raise ApiError(500, "INTERNAL_ERROR", str(exc)) from exc
