from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe, RecipeStats  # noqa: F401
from app.models.social import Like, Scrap
from app.models.user import User, UserProfile  # noqa: F401
from app.services.recipe_service import (
    AlreadyLikedError,
    AlreadyScrappedError,
    NotLikedError,
    NotScrappedError,
    RecipeNotFoundError,
    RecipeService,
)


def make_recipe(**overrides):
    values = {
        "recipe_id": 1,
        "title": "김치두부찌개",
        "summary": "김치와 두부로 끓이는 찌개",
        "description": "칼칼한 찌개",
        "ingredients_list": [],
        "instructions": ["김치를 볶는다.", "두부를 넣고 끓인다."],
        "steps": [],
        "servings": 2.0,
        "cooking_time_minutes": 20,
        "kcal_per_serving": 180,
        "difficulty": "easy",
        "category": ["한식"],
        "tags": ["얼큰한"],
        "tips": [],
        "main_image_url": "https://example.com/source.jpg",
        "source_url": "https://example.com/recipe",
        "author_type": "ADMIN",
        "created_at": None,
        "is_active": True,
        "stats": SimpleNamespace(likes_count=10, scrap_count=3),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_db(*scalar_results):
    """db.execute() 호출마다 scalar_one_or_none() 결과를 순서대로 반환하는 Mock DB."""
    db = MagicMock()
    mocks = []
    for r in scalar_results:
        m = MagicMock()
        m.scalar_one_or_none.return_value = r
        mocks.append(m)
    db.execute.side_effect = mocks
    return db


# ─── _to_list_item ───────────────────────────────────────────────────────────


def test_to_list_item_reads_counts_from_stats():
    service = RecipeService(None)
    recipe = make_recipe(stats=SimpleNamespace(likes_count=7, scrap_count=2))

    item = service._to_list_item(recipe)

    assert item.likes_count == 7
    assert item.scrap_count == 2


def test_to_list_item_defaults_to_zero_when_stats_missing():
    service = RecipeService(None)
    recipe = make_recipe(stats=None)

    item = service._to_list_item(recipe)

    assert item.likes_count == 0
    assert item.scrap_count == 0


def test_to_list_item_marks_liked_and_scrapped():
    service = RecipeService(None)
    recipe = make_recipe()

    item = service._to_list_item(recipe, liked_ids={1}, scrapped_ids={1})

    assert item.is_liked is True
    assert item.is_scrapped is True


def test_to_list_item_excludes_detail_fields():
    service = RecipeService(None)
    recipe = make_recipe()

    item = service._to_list_item(recipe)
    payload = item.model_dump()

    assert "ingredients" not in payload
    assert "steps" not in payload
    assert "description" not in payload
    assert "source_url" not in payload
    assert "ingredients_raw" not in payload
    assert payload["category"] == ["한식"]
    assert payload["tags"] == ["얼큰한"]


def test_to_detail_item_includes_structured_ingredients_with_raw_text():
    service = RecipeService(None)
    recipe = make_recipe(
        ingredients_list=[
            SimpleNamespace(
                group_name="메인",
                name="김치",
                amount_text="200g",
                quantity=200,
                unit="g",
                note="잘 익은 것",
                raw_text="김치 200g",
                is_optional=False,
            )
        ],
        steps=[
            SimpleNamespace(
                step_no=1,
                instruction="김치를 볶는다.",
                image_url="https://example.com/step.jpg",
                tip=None,
            )
        ],
    )

    item = service._to_detail_item(recipe)

    assert item.ingredients[0].raw_text == "김치 200g"
    assert item.ingredients[0].amount_text == "200g"
    assert item.steps[0].image_url == "https://example.com/step.jpg"
    assert item.source_url == "https://example.com/recipe"
    assert item.main_image_url == "https://example.com/source.jpg"


def test_to_list_item_not_in_sets():
    service = RecipeService(None)
    recipe = make_recipe()

    item = service._to_list_item(recipe, liked_ids={99}, scrapped_ids=set())

    assert item.is_liked is False
    assert item.is_scrapped is False


# ─── _get_active_recipe ──────────────────────────────────────────────────────


def test_get_active_recipe_raises_when_not_found():
    db = make_db(None)  # scalar_one_or_none → None
    service = RecipeService(db)

    with pytest.raises(RecipeNotFoundError):
        service._get_active_recipe(99)


def test_get_active_recipe_returns_recipe():
    recipe = make_recipe()
    db = make_db(recipe)
    service = RecipeService(db)

    result = service._get_active_recipe(1)

    assert result is recipe


# ─── like ────────────────────────────────────────────────────────────────────


def test_like_adds_like_and_commits():
    recipe = make_recipe()
    db = make_db(None)  # 기존 좋아요 없음
    db.get.return_value = SimpleNamespace(likes_count=11, scrap_count=3)
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    result = service.like(recipe_id=1, user_id=7)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, Like)
    assert added.user_id == 7
    assert added.recipe_id == 1
    db.commit.assert_called_once()
    assert result.likes_count == 11


def test_like_raises_if_already_liked():
    recipe = make_recipe()
    db = make_db(Like(user_id=7, recipe_id=1))  # 이미 좋아요 존재
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    with pytest.raises(AlreadyLikedError):
        service.like(recipe_id=1, user_id=7)

    db.add.assert_not_called()


def test_like_raises_if_recipe_not_found():
    service = RecipeService(MagicMock())
    service._get_active_recipe = MagicMock(side_effect=RecipeNotFoundError(99))

    with pytest.raises(RecipeNotFoundError):
        service.like(recipe_id=99, user_id=7)


# ─── unlike ──────────────────────────────────────────────────────────────────


def test_unlike_deletes_like_and_commits():
    recipe = make_recipe()
    existing = Like(user_id=7, recipe_id=1)
    db = make_db(existing)
    db.get.return_value = SimpleNamespace(likes_count=9, scrap_count=3)
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    result = service.unlike(recipe_id=1, user_id=7)

    db.delete.assert_called_once_with(existing)
    db.commit.assert_called_once()
    assert result.likes_count == 9


def test_unlike_raises_if_not_liked():
    recipe = make_recipe()
    db = make_db(None)  # 좋아요 없음
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    with pytest.raises(NotLikedError):
        service.unlike(recipe_id=1, user_id=7)

    db.delete.assert_not_called()


# ─── scrap ───────────────────────────────────────────────────────────────────


def test_scrap_adds_scrap_and_commits():
    recipe = make_recipe()
    db = make_db(None)  # 기존 스크랩 없음
    db.get.return_value = SimpleNamespace(likes_count=10, scrap_count=4)
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    result = service.scrap(recipe_id=1, user_id=7)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, Scrap)
    assert added.user_id == 7
    assert added.recipe_id == 1
    db.commit.assert_called_once()
    assert result.scrap_count == 4


def test_scrap_raises_if_already_scrapped():
    recipe = make_recipe()
    db = make_db(Scrap(user_id=7, recipe_id=1))  # 이미 스크랩 존재
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    with pytest.raises(AlreadyScrappedError):
        service.scrap(recipe_id=1, user_id=7)

    db.add.assert_not_called()


# ─── unscrap ─────────────────────────────────────────────────────────────────


def test_unscrap_deletes_scrap_and_commits():
    recipe = make_recipe()
    existing = Scrap(user_id=7, recipe_id=1)
    db = make_db(existing)
    db.get.return_value = SimpleNamespace(likes_count=10, scrap_count=2)
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    result = service.unscrap(recipe_id=1, user_id=7)

    db.delete.assert_called_once_with(existing)
    db.commit.assert_called_once()
    assert result.scrap_count == 2


def test_unscrap_raises_if_not_scrapped():
    recipe = make_recipe()
    db = make_db(None)  # 스크랩 없음
    service = RecipeService(db)
    service._get_active_recipe = lambda _: recipe

    with pytest.raises(NotScrappedError):
        service.unscrap(recipe_id=1, user_id=7)

    db.delete.assert_not_called()
