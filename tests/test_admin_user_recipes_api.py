from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1 import api as api_module
from app.api.v1.endpoints.admin import user_recipes as endpoint_module
from app.main import app
from app.models.recipe import UserRecipe
from app.services.user_recipe_service import (
    UserRecipeActiveDeleteError,
    _build_admin_user_recipe_cursor,
)

client = TestClient(app)


def _user_recipe(**overrides) -> UserRecipe:
    values = {
        "user_recipe_id": 11,
        "user_id": 7,
        "title": "Kimchi stew",
        "submission_text": "I made kimchi stew.",
        "draft_payload": {"description": "A spicy stew."},
        "ai_suggested_patch": {},
        "validation_errors": [],
        "status": "PENDING",
        "import_status": "NOT_IMPORTED",
        "is_active": True,
        "admin_note": None,
        "rejection_reason": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "imported_recipe_id": None,
        "imported_at": None,
        "created_at": datetime(2026, 5, 17, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 17, tzinfo=UTC),
    }
    values.update(overrides)
    return UserRecipe(**values)


class FakeUserRecipeService:
    def __init__(self, _db):
        self.recipe = _user_recipe()

    def get_admin_user_recipes(self, **kwargs):
        assert kwargs == {
            "status": "PENDING",
            "is_active": True,
            "user_id": 7,
            "q": "kimchi",
            "cursor": _build_admin_user_recipe_cursor(20),
            "limit": 1,
        }
        return [self.recipe], _build_admin_user_recipe_cursor(11)

    def get_active_user_recipe(self, user_recipe_id):
        if user_recipe_id == self.recipe.user_recipe_id:
            return self.recipe
        return None

    def hard_delete_inactive_user_recipe(self, user_recipe_id):
        return user_recipe_id == self.recipe.user_recipe_id


class FakeActiveDeleteBlockedService(FakeUserRecipeService):
    def hard_delete_inactive_user_recipe(self, user_recipe_id):
        raise UserRecipeActiveDeleteError


def _override_get_db():
    yield object()


def _override_require_admin():
    return object()


def setup_function():
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[api_module.require_admin] = _override_require_admin


def teardown_function():
    app.dependency_overrides.clear()


def test_admin_can_list_user_recipes(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get(
        "/api/v1/admin/user-recipes",
        params={
            "status": "PENDING",
            "is_active": True,
            "user_id": 7,
            "q": "kimchi",
            "cursor": _build_admin_user_recipe_cursor(20),
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] == _build_admin_user_recipe_cursor(11)
    assert body["has_next"] is True
    assert body["items"][0]["user_recipe_id"] == 11
    assert body["items"][0]["user_id"] == 7
    assert body["items"][0]["submission_text"] == "I made kimchi stew."
    assert body["items"][0]["import_status"] == "NOT_IMPORTED"
    assert body["items"][0]["is_active"] is True


def test_admin_can_get_user_recipe_detail(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/admin/user-recipes/11")

    assert response.status_code == 200
    body = response.json()
    assert body["user_recipe_id"] == 11
    assert body["draft_payload"]["description"] == "A spicy stew."
    assert body["draft_payload"]["ingredients"] == []
    assert body["ai_suggested_patch"]["description"] is None
    assert body["ai_suggested_patch"]["ingredients"] == []
    assert body["import_status"] == "NOT_IMPORTED"
    assert body["imported_recipe_id"] is None
    assert body["imported_at"] is None


def test_admin_user_recipe_detail_returns_404(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/admin/user-recipes/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_RECIPE_NOT_FOUND"


def test_admin_user_recipe_list_returns_400_for_invalid_cursor():
    response = client.get(
        "/api/v1/admin/user-recipes",
        params={"cursor": "1"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_admin_user_recipe_patch_rejects_is_active_change():
    response = client.patch(
        "/api/v1/admin/user-recipes/11",
        json={"is_active": False},
    )

    assert response.status_code == 422


def test_admin_can_hard_delete_inactive_user_recipe(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.delete("/api/v1/admin/user-recipes/11")

    assert response.status_code == 200
    assert response.json()["message"] == "제출 레시피가 삭제되었습니다."


def test_admin_cannot_hard_delete_active_user_recipe(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeActiveDeleteBlockedService,
    )

    response = client.delete("/api/v1/admin/user-recipes/11")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_RECIPE_ACTIVE"
