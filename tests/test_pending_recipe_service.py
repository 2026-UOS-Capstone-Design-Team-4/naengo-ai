from types import SimpleNamespace

import pytest

from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import PendingRecipe, Recipe, RecipeStats
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.schemas.pending_recipe import PendingRecipeAdminUpdate
from app.services import pending_recipe_service as service_module
from app.services.pending_recipe_service import (
    PendingRecipeApprovalError,
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


def make_pending_recipe(**overrides) -> PendingRecipe:
    values = {
        "pending_recipe_id": 1,
        "user_id": 7,
        "title": "김치두부찌개",
        "description": "칼칼한 찌개",
        "content": "김치와 두부를 넣고 끓입니다.",
        "ingredients": [{"name": "김치", "amount": "200", "unit": "g", "type": "메인"}],
        "ingredients_raw": "김치 200g, 두부 1모",
        "instructions": ["김치를 볶는다.", "두부를 넣고 끓인다."],
        "servings": 2,
        "cooking_time": 20,
        "calories": 180,
        "difficulty": "easy",
        "category": ["한식", "찌개"],
        "tags": ["얼큰한"],
        "tips": ["김치를 충분히 볶아주세요."],
        "video_url": "https://example.com/video",
        "image_url": "https://example.com/image.jpg",
        "status": "PENDING",
        "admin_note": None,
    }
    values.update(overrides)
    return PendingRecipe(**values)


def test_get_missing_recipe_fields_returns_required_missing_fields():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(description=None, ingredients=[], cooking_time=None)

    missing = service._get_missing_recipe_fields(pending)

    assert missing == ["description", "ingredients", "cooking_time"]


def test_pending_to_recipe_payload_sets_user_author_and_defaults_lists():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(tags=None, tips=None)

    payload = service._pending_to_recipe_payload(pending)

    assert payload["author_type"] == "USER"
    assert payload["author_id"] == pending.user_id
    assert payload["tags"] == []
    assert payload["tips"] == []


def test_update_pending_recipe_status_promotes_on_first_approval():
    db = FakeDb()
    service = PendingRecipeService(db)
    pending = make_pending_recipe()
    promoted = []
    service.get_active_pending_recipe = lambda _: pending
    service._promote_to_recipe = lambda recipe: promoted.append(recipe)

    result = service.update_pending_recipe_status(
        pending.pending_recipe_id,
        PendingRecipeAdminUpdate(status="APPROVED"),
    )

    assert result is pending
    assert pending.status == "APPROVED"
    assert pending.reviewed_at is not None
    assert promoted == [pending]
    assert db.committed is True
    assert db.refreshed is pending


def test_promote_to_recipe_rejects_missing_required_fields():
    service = PendingRecipeService(FakeDb())
    pending = make_pending_recipe(description=None)

    with pytest.raises(PendingRecipeApprovalError) as exc_info:
        service._promote_to_recipe(pending)

    assert "description" in str(exc_info.value)


def test_promote_to_recipe_creates_recipe_stats_and_embedding(monkeypatch):
    db = FakeDb()
    service = PendingRecipeService(db)
    pending = make_pending_recipe()
    service._find_existing_promoted_recipe = lambda _: None
    monkeypatch.setattr(
        service_module,
        "embedding_service",
        SimpleNamespace(embed_query=lambda text: [0.1, 0.2, 0.3]),
    )

    service._promote_to_recipe(pending)

    recipe = next(item for item in db.added if isinstance(item, Recipe))
    stats = next(item for item in db.added if isinstance(item, RecipeStats))
    assert recipe.title == pending.title
    assert recipe.author_type == "USER"
    assert recipe.author_id == pending.user_id
    assert recipe.embedding == [0.1, 0.2, 0.3]
    assert stats.recipe_id == 123
    assert db.flushed is True
