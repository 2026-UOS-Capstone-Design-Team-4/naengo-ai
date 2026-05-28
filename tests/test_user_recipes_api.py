from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1.endpoints import user_recipes as endpoint_module
from app.main import app
from app.models.recipe import (
    UserRecipe,
    UserRecipeLabel,
    UserRecipeReport,
    UserRecipeStep,
)
from app.models.user import User
from app.services.user_recipe_report_service import (
    UserRecipeReportAlreadyExistsError,
    UserRecipeReportOwnRecipeError,
)
from app.services.user_recipe_service import (
    UserRecipeInvalidCursorError,
    _build_public_user_recipe_cursor,
)

client = TestClient(app)


class FakeUserRecipeService:
    def __init__(self, _db):
        pass

    def get_approved_user_recipes(self, cursor=None, limit=20):
        self.cursor = cursor
        self.limit = limit
        recipe = _approved_user_recipe_list_item()
        return [recipe], _build_public_user_recipe_cursor(recipe)

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


class FakeUserRecipeReportService:
    def __init__(self, _db):
        pass

    def create_report(self, user_recipe_id, reporter_user_id, body):
        return UserRecipeReport(
            report_id=1,
            user_recipe_id=user_recipe_id,
            reporter_user_id=reporter_user_id,
            recipe_owner_user_id=8,
            reason=body.reason,
            description=body.description,
            status="PENDING",
            review_note=None,
            reviewed_by=None,
            reviewed_at=None,
            created_at=datetime(2026, 5, 25, tzinfo=UTC),
            updated_at=datetime(2026, 5, 25, tzinfo=UTC),
        )


class FakeAlreadyReportedService(FakeUserRecipeReportService):
    def create_report(self, user_recipe_id, reporter_user_id, body):
        raise UserRecipeReportAlreadyExistsError


class FakeOwnRecipeReportService(FakeUserRecipeReportService):
    def create_report(self, user_recipe_id, reporter_user_id, body):
        raise UserRecipeReportOwnRecipeError


def _fail_if_auth_is_required():
    raise AssertionError("public user recipe read should not require auth")


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
    app.dependency_overrides[endpoint_module.get_current_user_id] = (
        _fail_if_auth_is_required
    )

    response = client.get("/api/v1/user-recipes?cursor=abc&limit=3")

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] == _build_public_user_recipe_cursor(
        _approved_user_recipe_list_item()
    )
    assert body["has_next"] is True
    item = body["items"][0]
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


def test_approved_user_recipe_list_returns_400_for_invalid_cursor(monkeypatch):
    class InvalidCursorService(FakeUserRecipeService):
        def get_approved_user_recipes(self, cursor=None, limit=20):
            raise UserRecipeInvalidCursorError("Invalid cursor.")

    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        InvalidCursorService,
    )
    app.dependency_overrides[endpoint_module.get_current_user_id] = (
        _fail_if_auth_is_required
    )

    response = client.get("/api/v1/user-recipes?cursor=bad")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_approved_user_recipe_detail_returns_public_detail(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeService",
        FakeUserRecipeService,
    )
    app.dependency_overrides[endpoint_module.get_current_user_id] = (
        _fail_if_auth_is_required
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


def test_report_user_recipe_creates_pending_report(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeUserRecipeReportService,
    )

    response = client.post(
        "/api/v1/user-recipes/22/reports",
        json={
            "reason": "INAPPROPRIATE",
            "description": "부적절한 표현이 포함되어 있어요",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["report_id"] == 1
    assert body["user_recipe_id"] == 22
    assert body["reporter_user_id"] == 7
    assert body["recipe_owner_user_id"] == 8
    assert body["reason"] == "INAPPROPRIATE"
    assert body["status"] == "PENDING"


def test_report_user_recipe_returns_409_for_duplicate_report(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeAlreadyReportedService,
    )

    response = client.post(
        "/api/v1/user-recipes/22/reports",
        json={"reason": "SPAM"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_REPORTED"


def test_report_user_recipe_returns_409_for_own_recipe(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeOwnRecipeReportService,
    )

    response = client.post(
        "/api/v1/user-recipes/22/reports",
        json={"reason": "OTHER"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CANNOT_REPORT_OWN_RECIPE"


def _approved_user_recipe_list_item():
    return UserRecipe(
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
