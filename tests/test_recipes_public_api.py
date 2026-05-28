import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes as endpoint_module
from app.main import app
from app.schemas.recipe import (
    RecipeDetailResponse,
    RecipeListItemResponse,
    RecipeListResponse,
)

client = TestClient(app)


class FakeRecipeService:
    last_list_call = None
    last_detail_call = None

    def __init__(self, _db):
        pass

    def get_recipes_by_latest(self, user_id, cursor, limit):
        return self._get_recipe_list("latest", user_id, cursor, limit)

    def get_recipes_by_likes(self, user_id, cursor, limit):
        return self._get_recipe_list("likes", user_id, cursor, limit)

    def get_recipes_by_scraps(self, user_id, cursor, limit):
        return self._get_recipe_list("scraps", user_id, cursor, limit)

    def _get_recipe_list(self, sort, user_id, cursor, limit):
        FakeRecipeService.last_list_call = {
            "sort": sort,
            "user_id": user_id,
            "cursor": cursor,
            "limit": limit,
        }
        return RecipeListResponse(
            items=[
                RecipeListItemResponse(
                    id=1,
                    title="김치두부찌개",
                    summary="김치와 두부로 끓이는 찌개",
                    servings=2,
                    cooking_time_minutes=20,
                    difficulty="easy",
                    is_liked=False,
                    is_scrapped=False,
                )
            ],
            next_cursor=None,
            has_next=False,
        )

    def get_recipe(self, recipe_id, user_id):
        FakeRecipeService.last_detail_call = {
            "recipe_id": recipe_id,
            "user_id": user_id,
        }
        return RecipeDetailResponse(
            id=recipe_id,
            title="김치두부찌개",
            summary="김치와 두부로 끓이는 찌개",
            description="칼칼한 찌개",
            servings=2,
            cooking_time_minutes=20,
            difficulty="easy",
            author_type="ADMIN",
            is_liked=False,
            is_scrapped=False,
        )


def _override_get_db():
    yield object()


def setup_function():
    FakeRecipeService.last_list_call = None
    FakeRecipeService.last_detail_call = None
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db


def teardown_function():
    app.dependency_overrides.clear()


@pytest.mark.parametrize("sort", ["latest", "likes", "scraps"])
def test_get_recipes_allows_guest_and_returns_false_social_flags(monkeypatch, sort):
    monkeypatch.setattr(endpoint_module, "RecipeService", FakeRecipeService)

    response = client.get(f"/api/v1/recipes?sort={sort}&limit=1")

    assert response.status_code == 200
    assert response.json()["items"][0]["is_liked"] is False
    assert response.json()["items"][0]["is_scrapped"] is False
    assert FakeRecipeService.last_list_call == {
        "sort": sort,
        "user_id": None,
        "cursor": None,
        "limit": 1,
    }


def test_get_recipe_allows_guest_and_returns_false_social_flags(monkeypatch):
    monkeypatch.setattr(endpoint_module, "RecipeService", FakeRecipeService)

    response = client.get("/api/v1/recipes/1")

    assert response.status_code == 200
    assert response.json()["is_liked"] is False
    assert response.json()["is_scrapped"] is False
    assert FakeRecipeService.last_detail_call == {
        "recipe_id": 1,
        "user_id": None,
    }
