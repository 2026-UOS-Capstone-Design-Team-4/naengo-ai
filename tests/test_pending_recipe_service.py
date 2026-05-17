from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import PendingRecipe, Recipe
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.schemas.pending_recipe import PendingRecipeAdminUpdate
from app.services.pending_recipe_service import (
    PendingRecipeActiveDeleteError,
    PendingRecipeService,
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

    def refresh(self, item):
        self.refreshed = item

    def delete(self, item):
        self.deleted = item


def _draft(**overrides) -> dict:
    values = {
        "description": "Spicy kimchi tofu stew.",
        "ingredients": [
            {"name": "kimchi", "amount": "200", "unit": "g", "type": "main"}
        ],
        "ingredients_raw": "kimchi 200g, tofu 1 block",
        "instructions": ["Cook kimchi.", "Add tofu and simmer."],
        "servings": 2,
        "cooking_time_minutes": 20,
        "kcal_per_serving": 180,
        "difficulty": "easy",
        "category": ["Korean", "stew"],
        "tags": ["spicy"],
        "tips": ["Cook kimchi first."],
        "video_url": "https://example.com/video",
        "image_url": "https://example.com/image.jpg",
    }
    values.update(overrides)
    return values


def make_pending_recipe(**overrides) -> PendingRecipe:
    values = {
        "pending_recipe_id": 1,
        "user_id": 7,
        "title": "Kimchi tofu stew",
        "submission_text": "I cooked kimchi with tofu.",
        "draft_payload": _draft(),
        "ai_suggested_patch": {},
        "validation_errors": [],
        "status": "PENDING",
        "is_active": True,
        "admin_note": None,
    }
    values.update(overrides)
    return PendingRecipe(**values)


def test_update_pending_recipe_status_approves_without_recipe_import():
    db = FakeDb()
    service = PendingRecipeService(db)
    pending = make_pending_recipe()
    service.get_active_pending_recipe = lambda _: pending

    result = service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(status="APPROVED"),
    )

    assert result is pending
    assert pending.status == "APPROVED"
    assert pending.reviewed_at is not None
    assert pending.imported_recipe_id is None
    assert pending.imported_at is None
    assert not any(isinstance(item, Recipe) for item in db.added)
    assert db.committed is True
    assert db.refreshed is pending


def test_update_pending_recipe_replaces_draft_payload():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe()
    service.get_active_pending_recipe = lambda _: pending
    next_draft = _draft(description="Updated description")

    service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(draft_payload=next_draft),
    )

    assert pending.draft_payload == next_draft


def test_update_pending_recipe_normalizes_ai_suggested_patch():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe()
    service.get_active_pending_recipe = lambda _: pending

    service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(
            ai_suggested_patch={"description": "Use a clearer description."},
        ),
    )

    assert pending.ai_suggested_patch["description"] == "Use a clearer description."
    assert pending.ai_suggested_patch["ingredients"] == []
    assert pending.ai_suggested_patch["cooking_time_minutes"] is None


def test_update_pending_recipe_clears_rejection_reason_when_reopened():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(
        status="REJECTED",
        rejection_reason="내용이 부족합니다.",
    )
    service.get_active_pending_recipe = lambda _: pending

    service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(status="PENDING"),
    )

    assert pending.status == "PENDING"
    assert pending.rejection_reason is None


def test_update_pending_recipe_can_clear_nullable_admin_fields():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(
        admin_note="확인 필요",
        rejection_reason="내용이 부족합니다.",
    )
    service.get_active_pending_recipe = lambda _: pending

    service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(admin_note=None, rejection_reason=None),
    )

    assert pending.admin_note is None
    assert pending.rejection_reason is None


def test_delete_user_pending_recipe_marks_inactive():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe()
    service.get_user_pending_recipe = lambda *_: pending

    result = service.delete_user_pending_recipe(
        pending.pending_recipe_id,
        pending.user_id,
    )

    assert result is True
    assert pending.status == "PENDING"
    assert pending.is_active is False


def test_hard_delete_inactive_pending_recipe_deletes_row():
    db = FakeDb()
    service = PendingRecipeService(db)
    pending = make_pending_recipe(is_active=False)
    service.get_active_pending_recipe = lambda _: pending

    result = service.hard_delete_inactive_pending_recipe(
        pending.pending_recipe_id,
    )

    assert result is True
    assert db.deleted is pending
    assert db.committed is True


def test_hard_delete_active_pending_recipe_raises():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(is_active=True)
    service.get_active_pending_recipe = lambda _: pending

    try:
        service.hard_delete_inactive_pending_recipe(pending.pending_recipe_id)
    except PendingRecipeActiveDeleteError:
        pass
    else:
        raise AssertionError("Expected active hard delete to fail.")
