from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1 import api as api_module
from app.api.v1.endpoints.admin import pending_recipes as endpoint_module
from app.main import app
from app.models.recipe import PendingRecipe
from app.services.pending_recipe_service import (
    PendingRecipeActiveDeleteError,
    _build_admin_pending_recipe_cursor,
)

client = TestClient(app)


def _pending(**overrides) -> PendingRecipe:
    values = {
        "pending_recipe_id": 11,
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
    return PendingRecipe(**values)


class FakePendingRecipeService:
    def __init__(self, _db):
        self.pending = _pending()

    def get_admin_pending_recipes(self, **kwargs):
        assert kwargs == {
            "status": "PENDING",
            "is_active": True,
            "user_id": 7,
            "q": "kimchi",
            "cursor": _build_admin_pending_recipe_cursor(20),
            "limit": 1,
        }
        return [self.pending], _build_admin_pending_recipe_cursor(11)

    def get_active_pending_recipe(self, pending_recipe_id):
        if pending_recipe_id == self.pending.pending_recipe_id:
            return self.pending
        return None

    def hard_delete_inactive_pending_recipe(self, pending_recipe_id):
        return pending_recipe_id == self.pending.pending_recipe_id


class FakeActiveDeleteBlockedService(FakePendingRecipeService):
    def hard_delete_inactive_pending_recipe(self, pending_recipe_id):
        raise PendingRecipeActiveDeleteError


def _override_get_db():
    yield object()


def _override_require_admin():
    return object()


def setup_function():
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[api_module.require_admin] = _override_require_admin


def teardown_function():
    app.dependency_overrides.clear()


def test_admin_can_list_pending_recipes(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "PendingRecipeService",
        FakePendingRecipeService,
    )

    response = client.get(
        "/api/v1/admin/pending-recipes",
        params={
            "status": "PENDING",
            "is_active": True,
            "user_id": 7,
            "q": "kimchi",
            "cursor": _build_admin_pending_recipe_cursor(20),
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] == _build_admin_pending_recipe_cursor(11)
    assert body["has_next"] is True
    assert body["items"][0]["pending_recipe_id"] == 11
    assert body["items"][0]["user_id"] == 7
    assert body["items"][0]["submission_text"] == "I made kimchi stew."
    assert body["items"][0]["import_status"] == "NOT_IMPORTED"
    assert body["items"][0]["is_active"] is True


def test_admin_can_get_pending_recipe_detail(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "PendingRecipeService",
        FakePendingRecipeService,
    )

    response = client.get("/api/v1/admin/pending-recipes/11")

    assert response.status_code == 200
    body = response.json()
    assert body["pending_recipe_id"] == 11
    assert body["draft_payload"]["description"] == "A spicy stew."
    assert body["draft_payload"]["ingredients"] == []
    assert body["ai_suggested_patch"]["description"] is None
    assert body["ai_suggested_patch"]["ingredients"] == []
    assert body["import_status"] == "NOT_IMPORTED"
    assert body["imported_recipe_id"] is None
    assert body["imported_at"] is None


def test_admin_pending_recipe_detail_returns_404(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "PendingRecipeService",
        FakePendingRecipeService,
    )

    response = client.get("/api/v1/admin/pending-recipes/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PENDING_RECIPE_NOT_FOUND"


def test_admin_pending_recipe_list_returns_400_for_invalid_cursor():
    response = client.get(
        "/api/v1/admin/pending-recipes",
        params={"cursor": "1"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_admin_pending_recipe_patch_rejects_is_active_change():
    response = client.patch(
        "/api/v1/admin/pending-recipes/11",
        json={"is_active": False},
    )

    assert response.status_code == 422


def test_admin_can_hard_delete_inactive_pending_recipe(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "PendingRecipeService",
        FakePendingRecipeService,
    )

    response = client.delete("/api/v1/admin/pending-recipes/11")

    assert response.status_code == 200
    assert response.json()["message"] == "제출 레시피가 삭제되었습니다."


def test_admin_cannot_hard_delete_active_pending_recipe(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "PendingRecipeService",
        FakeActiveDeleteBlockedService,
    )

    response = client.delete("/api/v1/admin/pending-recipes/11")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PENDING_RECIPE_ACTIVE"
