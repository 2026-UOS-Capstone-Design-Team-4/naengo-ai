from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeClassification, RecipeIngredient
from app.services.recipe_retrieval_service import (
    _candidate_limit,
    _ingredient_match_strength,
    _ingredient_variants,
    _plan_bonus,
    _rerank_recipes,
)


def _recipe(
    recipe_id: int,
    ingredients: list[str],
    classification=None,
    difficulty: str = "easy",
    title: str | None = None,
) -> Recipe:
    recipe = Recipe(
        recipe_id=recipe_id,
        title=title or f"recipe {recipe_id}",
        description="test",
        servings=2,
        cooking_time_minutes=20,
        difficulty=difficulty,
    )
    recipe.ingredients_list = [
        RecipeIngredient(name=value, normalized_name=value) for value in ingredients
    ]
    recipe.classifications = classification
    return recipe


def test_rerank_prefers_available_and_required_ingredients():
    plan = SimpleNamespace(
        available_ingredients=["김치"],
        required_ingredients=["두부"],
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cooking_method=None,
        servings=None,
    )
    weak = _recipe(1, ["김치"])
    strong = _recipe(2, ["김치", "두부"])

    ranked = _rerank_recipes([weak, strong], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_rerank_uses_classification_soft_signals():
    plan = SimpleNamespace(
        available_ingredients=[],
        required_ingredients=[],
        taste_keywords=["spicy"],
        diet_keywords=["low_calorie"],
        dish_type="stew",
        cooking_method="boil",
        servings=None,
    )
    plain = _recipe(1, ["두부"])
    matched = _recipe(
        2,
        ["두부"],
        RecipeClassification(
            recipe_id=2,
            dish_type="stew",
            cooking_methods=["boil"],
            taste_keywords=["spicy"],
            diet_keywords=["low_calorie"],
        ),
    )

    ranked = _rerank_recipes([plain, matched], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_rerank_defaults_to_easier_recipes_when_difficulty_is_unspecified():
    plan = SimpleNamespace(
        available_ingredients=[],
        required_ingredients=[],
        difficulty=None,
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    hard = _recipe(1, ["감자"], difficulty="hard")
    normal = _recipe(2, ["감자"], difficulty="normal")
    easy = _recipe(3, ["감자"], difficulty="easy")

    ranked = _rerank_recipes([hard, normal, easy], plan)

    assert [recipe.recipe_id for recipe in ranked] == [3, 2, 1]


def test_rerank_honors_requested_hard_difficulty():
    plan = SimpleNamespace(
        available_ingredients=[],
        required_ingredients=[],
        difficulty="hard",
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    easy = _recipe(1, ["감자"], difficulty="easy")
    hard = _recipe(2, ["감자"], difficulty="hard")

    ranked = _rerank_recipes([easy, hard], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_rerank_prefers_requested_dish_name_in_title():
    plan = SimpleNamespace(
        target_dish_name="김치찌개",
        available_ingredients=["김치", "두부"],
        required_ingredients=[],
        difficulty=None,
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    ingredient_match = _recipe(1, ["김치", "두부"], title="두부 김치볶음")
    title_match = _recipe(2, ["김치"], title="돼지고기 김치찌개")

    ranked = _rerank_recipes([ingredient_match, title_match], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_rerank_matches_ingredient_synonyms():
    plan = SimpleNamespace(
        target_dish_name=None,
        available_ingredients=[],
        required_ingredients=["계란"],
        difficulty=None,
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    weak = _recipe(1, ["두부"])
    strong = _recipe(2, ["달걀"])

    ranked = _rerank_recipes([weak, strong], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_ingredient_variants_include_known_synonyms():
    assert _ingredient_variants("계란") == {"계란", "달걀"}
    assert "칵테일새우" in _ingredient_variants("새우")
    assert "대패삼겹살" in _ingredient_variants("삼겹살")


def test_rerank_strongly_prefers_all_main_ingredients():
    plan = SimpleNamespace(
        target_dish_name=None,
        available_ingredients=["미나리", "삼겹살"],
        main_ingredients=["미나리", "삼겹살"],
        required_ingredients=[],
        difficulty=None,
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    partial = _recipe(1, ["삼겹살"], title="삼겹살 구이")
    full = _recipe(2, ["미나리", "삼겹살"], title="미나리 삼겹살 볶음")

    ranked = _rerank_recipes([partial, full], plan)

    assert [recipe.recipe_id for recipe in ranked] == [2, 1]


def test_candidate_limit_expands_for_multiple_main_ingredients():
    plan = SimpleNamespace(main_ingredients=["미나리", "삼겹살"])

    assert _candidate_limit(3, plan) == 30


def test_ingredient_match_strength_distinguishes_exact_variant_and_substring():
    assert _ingredient_match_strength({"삼겹살"}, "삼겹살") == "exact"
    assert _ingredient_match_strength({"대패삼겹살"}, "삼겹살") == "variant"
    assert _ingredient_match_strength({"매운삼겹살양념"}, "삼겹살") == "substring"


def test_variant_main_ingredient_scores_lower_than_exact_match():
    plan = SimpleNamespace(
        target_dish_name=None,
        available_ingredients=[],
        main_ingredients=["삼겹살"],
        required_ingredients=[],
        difficulty="normal",
        taste_keywords=[],
        diet_keywords=[],
        dish_type=None,
        cuisine_type=None,
        cooking_method=None,
        servings=None,
    )
    exact = _recipe(1, ["삼겹살"], difficulty="normal")
    variant = _recipe(2, ["대패삼겹살"], difficulty="normal")

    assert _plan_bonus(exact, plan) > _plan_bonus(variant, plan)
