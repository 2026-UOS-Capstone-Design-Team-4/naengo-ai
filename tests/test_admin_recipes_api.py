from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1 import api as api_module
from app.api.v1.endpoints.admin import recipes as endpoint_module
from app.main import app
from app.models.recipe import Recipe

client = TestClient(app)


def _recipe(**overrides) -> Recipe:
    values = {
        "recipe_id": 101,
        "title": "Easy soup",
        "summary": "Simple soup",
        "description": "A simple soup.",
        "servings": 2,
        "cooking_time_minutes": 15,
        "kcal_per_serving": 120,
        "difficulty": "easy",
        "visibility": "PUBLIC",
        "author_type": "ADMIN",
        "source_id": None,
        "is_active": True,
        "created_at": datetime(2026, 5, 18, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 18, tzinfo=UTC),
    }
    values.update(overrides)
    return Recipe(**values)


class FakeAdminRecipeService:
    last_kwargs = None

    def __init__(self, _db):
        pass

    def get_recipes(self, **kwargs):
        FakeAdminRecipeService.last_kwargs = kwargs
        return [_recipe()], None


def _override_get_db():
    yield object()


def _override_get_current_user_id():
    return 1


def _override_require_admin():
    return object()


def setup_function():
    FakeAdminRecipeService.last_kwargs = None
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[
        endpoint_module.get_current_user_id
    ] = _override_get_current_user_id
    app.dependency_overrides[api_module.require_admin] = _override_require_admin


def teardown_function():
    app.dependency_overrides.clear()


def test_admin_recipe_list_accepts_difficulty_filter(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "AdminRecipeService",
        FakeAdminRecipeService,
    )

    response = client.get(
        "/api/v1/admin/recipes",
        params={"difficulty": "easy"},
    )

    assert response.status_code == 200
    assert FakeAdminRecipeService.last_kwargs["difficulty"] == "easy"
    assert response.json()["items"][0]["difficulty"] == "easy"


def test_admin_recipe_list_rejects_private_visibility(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "AdminRecipeService",
        FakeAdminRecipeService,
    )

    response = client.get(
        "/api/v1/admin/recipes",
        params={"visibility": "PRIVATE"},
    )

    assert response.status_code == 422
    assert FakeAdminRecipeService.last_kwargs is None
