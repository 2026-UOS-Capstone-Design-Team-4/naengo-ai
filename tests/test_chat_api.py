import asyncio

import pytest

from app.api.errors import ApiError
from app.api.v1.endpoints import chat as endpoint_module
from app.schemas.chat import ChatRequest


class FakeRoom:
    room_id = 11


class FakeChatService:
    def __init__(self, _db):
        pass

    def create_room(self, user_id, prompt):
        return FakeRoom()


class StorageFailingAgentService:
    async def stream(self, **kwargs):
        raise ApiError(
            503,
            "STORAGE_NOT_CONFIGURED",
            "이미지 전송을 위한 스토리지가 설정되지 않았습니다.",
        )


def test_create_room_and_chat_preserves_storage_api_error(monkeypatch):
    monkeypatch.setattr(endpoint_module, "ChatService", FakeChatService)
    monkeypatch.setattr(endpoint_module, "AgentService", StorageFailingAgentService)

    with pytest.raises(ApiError) as exc_info:
        asyncio.run(
            endpoint_module.create_room_and_chat(
                ChatRequest(
                    prompt="냉장고 사진으로 추천해줘",
                    image="data:image/jpeg;base64,/9j/4AAQSkZJRgAB",
                ),
                db=object(),
                current_user_id=1,
            )
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "STORAGE_NOT_CONFIGURED"
