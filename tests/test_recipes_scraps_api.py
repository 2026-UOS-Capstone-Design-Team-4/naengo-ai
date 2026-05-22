from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes as endpoint_module
from app.main import app
from app.schemas.recipe import RecipeListResponse
from app.services.recipe_service import RecipeInvalidCursorError

client = TestClient(app)


class FakeRecipeService:
    last_call = None

    def __init__(self, _db):
        pass

    def get_scraps(self, user_id, cursor, limit):
        FakeRecipeService.last_call = {
            "user_id": user_id,
            "cursor": cursor,
            "limit": limit,
        }
        return RecipeListResponse(items=[], next_cursor=None, has_next=False)


class FakeInvalidCursorRecipeService(FakeRecipeService):
    def get_scraps(self, user_id, cursor, limit):
        raise RecipeInvalidCursorError


def _override_get_db():
    yield object()


def _override_current_user_id():
    return 7


def setup_function():
    FakeRecipeService.last_call = None
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[endpoint_module.get_current_user_id] = (
        _override_current_user_id
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_get_scrapped_recipes_uses_current_user_scrap_listing(monkeypatch):
    monkeypatch.setattr(endpoint_module, "RecipeService", FakeRecipeService)

    response = client.get("/api/v1/recipes/scraps?cursor=abc&limit=3")

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None, "has_next": False}
    assert FakeRecipeService.last_call == {
        "user_id": 7,
        "cursor": "abc",
        "limit": 3,
    }


def test_get_scrapped_recipes_returns_invalid_cursor(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "RecipeService",
        FakeInvalidCursorRecipeService,
    )

    response = client.get("/api/v1/recipes/scraps?cursor=bad")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_users_me_scraps_route_is_not_registered():
    paths = app.openapi()["paths"]

    assert "/api/v1/users/me/scraps" not in paths
    assert "/api/v1/recipes/bookmarks" not in paths
    assert "/api/v1/recipes/scraps" in paths
