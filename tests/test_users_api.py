from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import users as endpoint_module
from app.main import app

client = TestClient(app)


class FakeUserService:
    def __init__(self, _db):
        pass

    def get_user(self, user_id):
        return SimpleNamespace(
            user_id=user_id,
            username="naengo_user_123",
            nickname="냉장고요리왕",
            role="USER",
            is_active=True,
            is_blocked=False,
            user_identities=[
                SimpleNamespace(
                    id=1,
                    provider="KAKAO",
                    email="user@example.com",
                    provider_user_id="external-id",
                    created_at=datetime(2026, 4, 1, tzinfo=UTC),
                ),
            ],
            created_at=datetime(2026, 4, 1, tzinfo=UTC),
            updated_at=datetime(2026, 5, 22, tzinfo=UTC),
        )


def _override_get_db():
    yield object()


def _override_get_current_user_id():
    return 7


def setup_function():
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[endpoint_module.get_current_user_id] = (
        _override_get_current_user_id
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_get_me_returns_username_and_user_identities(monkeypatch):
    monkeypatch.setattr(endpoint_module, "UserService", FakeUserService)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 7
    assert body["username"] == "naengo_user_123"
    assert body["user_identities"] == [
        {
            "id": 1,
            "provider": "KAKAO",
            "email": "user@example.com",
            "created_at": "2026-04-01T00:00:00Z",
        }
    ]
    assert "provider_user_id" not in body["user_identities"][0]
