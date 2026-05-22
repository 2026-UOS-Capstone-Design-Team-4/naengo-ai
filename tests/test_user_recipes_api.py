from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.endpoints import user_recipes as endpoint_module
from app.main import app
from app.models.recipe import UserRecipe, UserRecipeLabel

client = TestClient(app)


class FakeUserRecipeService:
    def __init__(self, _db):
        pass

    def get_user_recipes(self, user_id):
        return [
            UserRecipe(
                user_recipe_id=11,
                user_id=user_id,
                title="Kimchi stew",
                description="A spicy stew.",
                servings=2,
                cooking_time_minutes=25,
                kcal_per_serving=320,
                difficulty="easy",
                source_main_image_url="https://example.com/kimchi.jpg",
                labels=[
                    UserRecipeLabel(label_type="CATEGORY", label_value="찌개"),
                    UserRecipeLabel(label_type="TAG", label_value="얼큰함"),
                ],
                ingredients=[],
                steps=[],
                status="PENDING",
                import_status="NOT_IMPORTED",
                is_active=True,
                rejection_reason=None,
                created_at=datetime(2026, 5, 17, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, tzinfo=UTC),
            )
        ]


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


def test_user_recipe_list_returns_card_fields_without_detail_arrays(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/user-recipes")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["user_recipe_id"] == 11
    assert item["category"] == ["찌개"]
    assert item["tags"] == ["얼큰함"]
    assert "ingredients" not in item
    assert "steps" not in item
    assert "labels" not in item
    assert "nutrition" not in item
