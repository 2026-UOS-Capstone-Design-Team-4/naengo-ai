import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.errors import ApiError
from app.api.v1.openapi.guest_chat import GUEST_CHAT_DESCRIPTION, GUEST_CHAT_RESPONSES
from app.schemas.guest_chat import GuestChatRequest, history_to_model_messages
from app.services.agent_service import AgentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    summary="게스트 채팅",
    description=GUEST_CHAT_DESCRIPTION,
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
