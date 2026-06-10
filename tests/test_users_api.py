from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import users as endpoint_module
from app.main import app
from app.services.user_profile_input_service import (
    UserProfileInputFact,
    UserProfileInputResult,
)

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


class FakeWithdrawUserService:
    called_user_id = None
    result = True

    def __init__(self, _db):
        pass

    def withdraw_user(self, user_id):
        type(self).called_user_id = user_id
        return type(self).result


class FakeProfileUserService:
    captured_facts = None

    def __init__(self, _db):
        pass

    def get_profile(self, user_id):
        return SimpleNamespace(user_id=user_id)

    def append_profile_user_input(self, user_id, body, facts=None):
        type(self).captured_facts = facts
        return {"user_input": [body.text]}


class FakeProfileNormalizer:
    def normalize(self, text):
        return UserProfileInputResult(
            is_user_info=True,
            normalized_sentence="저탄수 식단을 선호해요.",
            facts=[
                UserProfileInputFact(
                    field="dietary_restrictions",
                    value="저탄수화물",
                )
            ],
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


def test_delete_me_withdraws_current_user(monkeypatch):
    FakeWithdrawUserService.called_user_id = None
    FakeWithdrawUserService.result = True
    monkeypatch.setattr(endpoint_module, "UserService", FakeWithdrawUserService)

    response = client.delete("/api/v1/users/me")

    assert response.status_code == 204
    assert response.content == b""
    assert FakeWithdrawUserService.called_user_id == 7


def test_delete_me_returns_not_found_when_user_missing(monkeypatch):
    FakeWithdrawUserService.called_user_id = None
    FakeWithdrawUserService.result = False
    monkeypatch.setattr(endpoint_module, "UserService", FakeWithdrawUserService)

    response = client.delete("/api/v1/users/me")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "사용자를 찾을 수 없습니다.",
            "details": {},
        }
    }
    assert FakeWithdrawUserService.called_user_id == 7


def test_append_profile_passes_structured_facts_to_service(monkeypatch):
    FakeProfileUserService.captured_facts = None
    monkeypatch.setattr(endpoint_module, "UserService", FakeProfileUserService)
    monkeypatch.setattr(
        endpoint_module,
        "user_profile_input_normalizer",
        FakeProfileNormalizer(),
    )

    response = client.post(
        "/api/v1/users/me/profile",
        json={"text": "저탄수 식단을 선호해"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_input": ["저탄수 식단을 선호해요."]}
    assert FakeProfileUserService.captured_facts[0].field == (
        "dietary_restrictions"
    )
    assert FakeProfileUserService.captured_facts[0].value == "저탄수화물"
