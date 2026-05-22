from pydantic import ValidationError

from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe, UserRecipe
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.schemas.user_recipe import UserRecipeAdminUpdate, UserRecipeCreate
from app.services.user_recipe_service import (
    UserRecipeActiveDeleteError,
    UserRecipeImageUpload,
    UserRecipeImageValidationError,
    UserRecipeService,
)


class FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False
        self.flushed = False
        self.refreshed = None

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True
        for item in self.added:
            if isinstance(item, Recipe):
                item.recipe_id = 123
            if isinstance(item, UserRecipe):
                item.user_recipe_id = 456

    def refresh(self, item):
        self.refreshed = item

    def delete(self, item):
        self.deleted = item


class FakeUserQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *_):
        return self

    def first(self):
        return self.user


class FakeCreateDb(FakeDb):
    def __init__(self, user):
        super().__init__()
        self.user = user

    def query(self, model):
        return FakeUserQuery(self.user)


class FakeImageStorage:
    def __init__(self):
        self.uploads = []

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str:
        self.uploads.append((data, key, content_type))
        return f"https://storage.local/{key}"


def make_user_recipe(**overrides) -> UserRecipe:
    values = {
        "user_recipe_id": 1,
        "user_id": 7,
        "title": "Kimchi tofu stew",
        "description": "Spicy kimchi tofu stew.",
        "servings": 2,
        "cooking_time_minutes": 20,
        "kcal_per_serving": 180,
        "difficulty": "easy",
        "status": "PENDING",
        "is_active": True,
    }
    values.update(overrides)
    return UserRecipe(**values)


def test_create_user_recipe_stores_structured_payload():
    db = FakeCreateDb(User(user_id=7, username="u@example.com", nickname="user"))
    service = UserRecipeService(db)

    result = service.create_user_recipe(
        UserRecipeCreate(
            title="엄마 김치찌개",
            description="묵은지로 끓인 진한 김치찌개입니다.",
            servings=2,
            cooking_time_minutes=25,
            difficulty="easy",
            ingredients=[{"name": "묵은지", "amount_text": "300g"}],
            steps=[{"step_no": 1, "instruction": "묵은지를 볶습니다."}],
        ),
        user_id=7,
    )

    assert result is db.added[0]
    assert result.title == "엄마 김치찌개"
    assert result.description == "묵은지로 끓인 진한 김치찌개입니다."
    assert result.ingredients[0].name == "묵은지"
    assert result.steps[0].instruction == "묵은지를 볶습니다."
    assert db.flushed is True
    assert db.committed is True
    assert db.refreshed is result


def test_create_user_recipe_uploads_main_and_step_images():
    db = FakeCreateDb(User(user_id=7, username="u@example.com", nickname="user"))
    storage = FakeImageStorage()
    service = UserRecipeService(db, image_storage=storage)

    result = service.create_user_recipe(
        UserRecipeCreate(
            title="엄마 김치찌개",
            description="묵은지 김치찌개",
            servings=2,
            cooking_time_minutes=25,
            difficulty="easy",
            ingredients=[{"name": "묵은지"}],
            steps=[
                {
                    "step_no": 1,
                    "instruction": "묵은지를 볶습니다.",
                    "client_image_key": "step-1",
                }
            ],
        ),
        user_id=7,
        main_image=UserRecipeImageUpload(
            filename="main.jpg",
            content_type="image/jpeg",
            data=b"main",
        ),
        step_images=[
            UserRecipeImageUpload(
                filename="step-1.png",
                content_type="image/png",
                data=b"step",
            )
        ],
    )

    assert result.source_main_image_url.startswith(
        "https://storage.local/user-recipes/7/456/main/",
    )
    assert result.steps[0].image_url.startswith(
        "https://storage.local/user-recipes/7/456/steps/1/",
    )
    assert len(storage.uploads) == 2


def test_create_user_recipe_rejects_unmatched_step_image():
    db = FakeCreateDb(User(user_id=7, username="u@example.com", nickname="user"))
    service = UserRecipeService(db, image_storage=FakeImageStorage())

    try:
        service.create_user_recipe(
            UserRecipeCreate(
                title="엄마 김치찌개",
                description="묵은지 김치찌개",
                servings=2,
                cooking_time_minutes=25,
                difficulty="easy",
                ingredients=[{"name": "묵은지"}],
                steps=[{"step_no": 1, "instruction": "묵은지를 볶습니다."}],
            ),
            user_id=7,
            step_images=[
                UserRecipeImageUpload(
                    filename="step-1.png",
                    content_type="image/png",
                    data=b"step",
                )
            ],
        )
    except UserRecipeImageValidationError as exc:
        assert "Unmatched step images: step-1" in str(exc)
    else:
        raise AssertionError("Expected unmatched step image to be rejected.")


def test_create_user_recipe_rejects_missing_step_image():
    db = FakeCreateDb(User(user_id=7, username="u@example.com", nickname="user"))
    service = UserRecipeService(db, image_storage=FakeImageStorage())

    try:
        service.create_user_recipe(
            UserRecipeCreate(
                title="엄마 김치찌개",
                description="묵은지 김치찌개",
                servings=2,
                cooking_time_minutes=25,
                difficulty="easy",
                ingredients=[{"name": "묵은지"}],
                steps=[
                    {
                        "step_no": 1,
                        "instruction": "묵은지를 볶습니다.",
                        "client_image_key": "step-1",
                    }
                ],
            ),
            user_id=7,
        )
    except UserRecipeImageValidationError as exc:
        assert "Missing step images: step-1" in str(exc)
    else:
        raise AssertionError("Expected missing step image to be rejected.")


def test_user_recipe_create_rejects_server_managed_fields():
    try:
        UserRecipeCreate(
            title="김치찌개",
            description="김치찌개를 만들었어요.",
            servings=2,
            cooking_time_minutes=20,
            difficulty="easy",
            ingredients=[{"name": "김치"}],
            steps=[{"step_no": 1, "instruction": "끓입니다."}],
            status="APPROVED",
        )
    except ValidationError as exc:
        error_locations = {tuple(error["loc"]) for error in exc.errors()}
    else:
        raise AssertionError("Expected server-managed fields to be rejected.")

    assert ("status",) in error_locations


def test_user_recipe_create_requires_title():
    try:
        UserRecipeCreate(
            description="묵은지로 끓인 찌개입니다.",
            servings=2,
            cooking_time_minutes=20,
            difficulty="easy",
            ingredients=[{"name": "김치"}],
            steps=[{"step_no": 1, "instruction": "끓입니다."}],
        )
    except ValidationError as exc:
        error_locations = {tuple(e["loc"]) for e in exc.errors()}
    else:
        raise AssertionError("title should be required")
    assert ("title",) in error_locations


def test_update_user_recipe_status_approves_without_recipe_import():
    db = FakeDb()
    service = UserRecipeService(db)
    pending = make_user_recipe()
    service.get_active_user_recipe = lambda _: pending

    result = service.update_user_recipe_status(
        pending.user_recipe_id,
        UserRecipeAdminUpdate(status="APPROVED"),
    )

    assert result is pending
    assert pending.status == "APPROVED"
    assert pending.reviewed_at is not None
    assert pending.imported_recipe_id is None
    assert pending.imported_at is None
    assert not any(isinstance(item, Recipe) for item in db.added)
    assert db.committed is True
    assert db.refreshed is pending


def test_update_user_recipe_replaces_structured_recipe_fields():
    service = UserRecipeService(FakeDb())
    pending = make_user_recipe()
    service.get_active_user_recipe = lambda _: pending

    service.update_user_recipe_status(
        pending.user_recipe_id,
        UserRecipeAdminUpdate(
            description="Updated description",
            ingredients=[
                {
                    "name": "kimchi",
                    "amount_text": "200g",
                    "unit": "g",
                    "sort_order": 1,
                }
            ],
            steps=[
                {
                    "step_no": 1,
                    "instruction": "Cook kimchi.",
                    "sort_order": 1,
                }
            ],
        ),
    )

    assert pending.description == "Updated description"
    assert pending.ingredients[0].name == "kimchi"
    assert pending.ingredients[0].amount_text == "200g"
    assert pending.steps[0].instruction == "Cook kimchi."


def test_update_user_recipe_clears_rejection_reason_when_reopened():
    service = UserRecipeService(FakeDb())
    pending = make_user_recipe(
        status="REJECTED",
        rejection_reason="내용이 부족합니다.",
    )
    service.get_active_user_recipe = lambda _: pending

    service.update_user_recipe_status(
        pending.user_recipe_id,
        UserRecipeAdminUpdate(status="PENDING"),
    )

    assert pending.status == "PENDING"
    assert pending.rejection_reason is None


def test_update_user_recipe_can_clear_rejection_reason():
    service = UserRecipeService(FakeDb())
    pending = make_user_recipe(
        rejection_reason="내용이 부족합니다.",
    )
    service.get_active_user_recipe = lambda _: pending

    service.update_user_recipe_status(
        pending.user_recipe_id,
        UserRecipeAdminUpdate(rejection_reason=None),
    )

    assert pending.rejection_reason is None


def test_delete_user_recipe_marks_inactive():
    service = UserRecipeService(FakeDb())
    pending = make_user_recipe()
    service.get_user_recipe = lambda *_: pending

    result = service.delete_user_recipe(
        pending.user_recipe_id,
        pending.user_id,
    )

    assert result is True
    assert pending.status == "PENDING"
    assert pending.is_active is False


def test_hard_delete_inactive_user_recipe_deletes_row():
    db = FakeDb()
    service = UserRecipeService(db)
    pending = make_user_recipe(is_active=False)
    service.get_active_user_recipe = lambda _: pending

    result = service.hard_delete_inactive_user_recipe(
        pending.user_recipe_id,
    )

    assert result is True
    assert db.deleted is pending
    assert db.committed is True


def test_hard_delete_active_user_recipe_raises():
    service = UserRecipeService(FakeDb())
    pending = make_user_recipe(is_active=True)
    service.get_active_user_recipe = lambda _: pending

    try:
        service.hard_delete_inactive_user_recipe(pending.user_recipe_id)
    except UserRecipeActiveDeleteError:
        pass
    else:
        raise AssertionError("Expected active hard delete to fail.")
