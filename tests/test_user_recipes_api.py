from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.endpoints import user_recipes as endpoint_module
from app.main import app
from app.models.recipe import UserRecipe, UserRecipeLabel, UserRecipeStep
from app.models.user import User

client = TestClient(app)


class FakeUserRecipeService:
    def __init__(self, _db):
        pass

    def get_approved_user_recipes(self):
        return [
            UserRecipe(
                user_recipe_id=22,
                user_id=8,
                title="Approved kimchi stew",
                description="A public approved recipe.",
                servings=2,
                cooking_time_minutes=25,
                kcal_per_serving=320,
                difficulty="easy",
                main_image_url="https://example.com/approved-kimchi.jpg",
                user=User(
                    user_id=8,
                    username="author@example.com",
                    nickname="레시피작성자",
                ),
                labels=[
                    UserRecipeLabel(
                        label_type="CATEGORY",
                        label_value="찌개",
                        source="ADMIN",
                        sort_order=1,
                    ),
                    UserRecipeLabel(
                        label_type="TAG",
                        label_value="얼큰함",
                        source="ADMIN",
                        sort_order=2,
                    ),
                ],
                ingredients=[],
                steps=[],
                status="APPROVED",
                import_status="NOT_IMPORTED",
                is_active=True,
                rejection_reason=None,
                created_at=datetime(2026, 5, 18, tzinfo=UTC),
                updated_at=datetime(2026, 5, 18, tzinfo=UTC),
            )
        ]

    def get_approved_user_recipe(self, user_recipe_id):
        if user_recipe_id != 22:
            return None
        return UserRecipe(
            user_recipe_id=user_recipe_id,
            user_id=8,
            title="Approved kimchi stew",
            description="A public approved recipe.",
            servings=2,
            cooking_time_minutes=25,
            kcal_per_serving=320,
            difficulty="easy",
            main_image_url="https://example.com/approved-kimchi.jpg",
            user=User(
                user_id=8,
                username="author@example.com",
                nickname="레시피작성자",
            ),
            labels=[
                UserRecipeLabel(
                    label_type="CATEGORY",
                    label_value="찌개",
                    source="ADMIN",
                    sort_order=1,
                ),
                UserRecipeLabel(
                    label_type="TAG",
                    label_value="얼큰함",
                    source="ADMIN",
                    sort_order=2,
                ),
                UserRecipeLabel(
                    label_type="TIP",
                    label_value="묵은지를 쓰면 좋아요",
                    source="ADMIN",
                    sort_order=3,
                ),
            ],
            ingredients=[],
            steps=[
                UserRecipeStep(
                    step_no=1,
                    instruction="김치를 볶습니다.",
                    image_url="https://example.com/approved-step-1.jpg",
                    sort_order=1,
                )
            ],
            status="APPROVED",
            import_status="NOT_IMPORTED",
            is_active=True,
            rejection_reason=None,
            created_at=datetime(2026, 5, 18, tzinfo=UTC),
            updated_at=datetime(2026, 5, 18, tzinfo=UTC),
        )

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
                main_image_url="https://example.com/kimchi.jpg",
                labels=[
                    UserRecipeLabel(
                        label_type="CATEGORY",
                        label_value="찌개",
                        source="ADMIN",
                        sort_order=1,
                    ),
                    UserRecipeLabel(
                        label_type="TAG",
                        label_value="얼큰함",
                        source="ADMIN",
                        sort_order=2,
                    ),
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

    def get_user_recipe(self, user_recipe_id, user_id):
        if user_recipe_id != 11:
            return None
        return UserRecipe(
            user_recipe_id=user_recipe_id,
            user_id=user_id,
            title="Kimchi stew",
            description="A spicy stew.",
            servings=2,
            cooking_time_minutes=25,
            kcal_per_serving=320,
            difficulty="easy",
            main_image_url="https://example.com/kimchi.jpg",
            labels=[
                UserRecipeLabel(
                    label_type="CATEGORY",
                    label_value="찌개",
                    source="ADMIN",
                    sort_order=1,
                ),
                UserRecipeLabel(
                    label_type="TAG",
                    label_value="얼큰함",
                    source="ADMIN",
                    sort_order=2,
                ),
                UserRecipeLabel(
                    label_type="TIP",
                    label_value="묵은지를 쓰면 좋아요",
                    source="ADMIN",
                    sort_order=3,
                ),
            ],
            ingredients=[],
            steps=[
                UserRecipeStep(
                    step_no=1,
                    instruction="김치를 볶습니다.",
                    image_url="https://example.com/step-1.jpg",
                    sort_order=1,
                )
            ],
            status="PENDING",
            import_status="NOT_IMPORTED",
            is_active=True,
            rejection_reason=None,
            created_at=datetime(2026, 5, 17, tzinfo=UTC),
            updated_at=datetime(2026, 5, 17, tzinfo=UTC),
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


def test_approved_user_recipe_list_returns_public_approved_recipes(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/user-recipes")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["user_recipe_id"] == 22
    assert item["user_id"] == 8
    assert item["user"] == {"user_id": 8, "nickname": "레시피작성자"}
    assert item["status"] == "APPROVED"
    assert item["category"] == ["찌개"]
    assert item["tags"] == ["얼큰함"]
    assert "ingredients" not in item
    assert "steps" not in item
    assert "labels" not in item
    assert "nutrition" not in item


def test_approved_user_recipe_detail_returns_public_detail(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/user-recipes/22")

    assert response.status_code == 200
    body = response.json()
    assert body["user_recipe_id"] == 22
    assert body["user_id"] == 8
    assert body["user"] == {"user_id": 8, "nickname": "레시피작성자"}
    assert body["status"] == "APPROVED"
    assert body["category"] == ["찌개"]
    assert body["tags"] == ["얼큰함"]
    assert body["tips"] == ["묵은지를 쓰면 좋아요"]
    assert body["main_image_url"] == "https://example.com/approved-kimchi.jpg"
    assert body["steps"][0]["image_url"] == "https://example.com/approved-step-1.jpg"


def test_my_user_recipe_list_returns_card_fields_without_detail_arrays(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/user-recipes/me")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["user_recipe_id"] == 11
    assert item["user_id"] == 7
    assert item["status"] == "PENDING"
    assert item["category"] == ["찌개"]
    assert item["tags"] == ["얼큰함"]
    assert "ingredients" not in item
    assert "steps" not in item
    assert "labels" not in item
    assert "nutrition" not in item


def test_my_user_recipe_detail_returns_category_tags_and_step_image(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )

    response = client.get("/api/v1/user-recipes/me/11")

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == ["찌개"]
    assert body["tags"] == ["얼큰함"]
    assert body["tips"] == ["묵은지를 쓰면 좋아요"]
    assert body["main_image_url"] == "https://example.com/kimchi.jpg"
    assert body["steps"][0]["image_url"] == "https://example.com/step-1.jpg"
