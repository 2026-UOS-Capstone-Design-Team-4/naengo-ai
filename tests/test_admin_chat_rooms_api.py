from fastapi.testclient import TestClient

from app.api.v1 import api as api_module
from app.api.v1.endpoints.admin import chat_rooms as endpoint_module
from app.main import app
from app.services.admin_chat_room_service import AdminChatRoomNotFoundError

client = TestClient(app)


class FakeAdminChatRoomService:
    def __init__(self, _db):
        pass

    def hard_delete_room(self, room_id):
        if room_id == 404:
            raise AdminChatRoomNotFoundError(room_id)


def _override_get_db():
    yield object()


def _override_require_admin():
    return object()


def setup_function():
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[api_module.require_admin] = _override_require_admin


def teardown_function():
    app.dependency_overrides.clear()


def test_admin_can_hard_delete_chat_room(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "AdminChatRoomService",
        FakeAdminChatRoomService,
    )

    response = client.delete("/api/v1/admin/chat-rooms/11")

    assert response.status_code == 204
    assert response.content == b""


def test_admin_chat_room_delete_returns_404(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "AdminChatRoomService",
        FakeAdminChatRoomService,
    )

    response = client.delete("/api/v1/admin/chat-rooms/404")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHAT_ROOM_NOT_FOUND"
