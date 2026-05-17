from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.services.ingestion.foodsafetykorea_ingredient_parser_service import (
    FoodsafetyKoreaIngredient,
)
from app.services.ingestion.recipe_text_rewrite_service import draft_from_extraction
from scripts.parse_foodsafetykorea_sources import (
    AIRecipeMetadataExtractor,
    ExtractionBuildError,
    RecipeMetadata,
    RecipeMetadataOutput,
    build_extraction,
    validate,
)


class FakeIngredientParser:
    def parse(
        self, title: str, raw_ingredients: str
    ) -> list[FoodsafetyKoreaIngredient]:
        assert title == "shrimp tofu stew"
        assert "tofu 75g" in raw_ingredients
        return [
            FoodsafetyKoreaIngredient(
                group_name="main",
                name="tofu",
                normalized_name="tofu",
                amount_text="75g",
                quantity="75",
                unit="g",
                raw_text="tofu 75g",
            ),
            FoodsafetyKoreaIngredient(
                group_name="main",
                name="shrimp",
                normalized_name="shrimp",
                amount_text="30g",
                quantity="30",
                unit="g",
                raw_text="shrimp 30g",
            ),
        ]


class FakeTextRewriter:
    def rewrite(self, extraction):
        draft = draft_from_extraction(extraction)
        return replace(
            draft,
            title="soft shrimp tofu stew",
            description="A simple side dish with shrimp and tofu.",
            ingredients=[
                replace(draft.ingredients[0], raw_text="tofu 75g"),
                replace(draft.ingredients[1], raw_text="shrimp 30g"),
            ],
            steps=[
                replace(
                    draft.steps[0],
                    instruction="Blanch the shrimp in boiling water.",
                )
            ],
        )


class FakeMetadataExtractor:
    def extract(self, row, title, ingredients, steps):
        return RecipeMetadata(
            servings=2,
            cooking_time_minutes=30,
            kcal_per_serving=220,
        )


class NullMetadataExtractor:
    def extract(self, row, title, ingredients, steps):
        return RecipeMetadata(servings=None, cooking_time_minutes=None)


class FailingMetadataExtractor:
    def extract(self, row, title, ingredients, steps):
        pytest.fail("metadata AI should not be called")


class FakeMetadataAgent:
    def __init__(self, output: RecipeMetadataOutput):
        self.output = output
        self.prompt = None

    def run_sync(self, prompt: str):
        self.prompt = prompt
        return SimpleNamespace(output=self.output)


class PassthroughTextRewriter:
    def rewrite(self, extraction):
        return draft_from_extraction(extraction)


class IngredientParser:
    def __init__(self, ingredients: list[FoodsafetyKoreaIngredient]):
        self.ingredients = ingredients

    def parse(
        self, title: str, raw_ingredients: str
    ) -> list[FoodsafetyKoreaIngredient]:
        return self.ingredients


def _ingredient(index: int) -> FoodsafetyKoreaIngredient:
    return FoodsafetyKoreaIngredient(
        group_name="main",
        name=f"ingredient{index}",
        normalized_name=f"ingredient{index}",
        amount_text="1g",
        quantity="1",
        unit="g",
        raw_text=f"ingredient{index} 1g",
    )


def _row(step_count: int) -> dict:
    return {
        "id": "28",
        "name": "test recipe",
        "ingredients": "ingredient",
        "manual_steps": [
            {"step": index, "description": f"{index}. Cook {index}"}
            for index in range(1, step_count + 1)
        ],
    }


def test_build_foodsafetykorea_extraction_uses_ingredient_parser_and_text_rewriter():
    row = {
        "id": "28",
        "name": "shrimp tofu stew",
        "method": "boil",
        "category": "side dish",
        "serving_weight": "120",
        "nutrition": {
            "calories": "220",
            "carbohydrate": "3",
            "protein": "14",
            "fat": "17",
            "sodium": "99",
        },
        "ingredients": "tofu 75g, shrimp 30g",
        "manual_steps": [
            {
                "step": 1,
                "description": "1. Blanch the shrimp.",
                "image_url": "https://example.com/step.jpg",
            }
        ],
        "low_sodium_tip": "Use low-sodium seasoning.",
        "image_small_url": "https://example.com/small.jpg",
        "image_large_url": "https://example.com/large.jpg",
    }

    extraction = build_extraction(
        row,
        ingredient_parser=FakeIngredientParser(),
        text_rewriter=FakeTextRewriter(),
        metadata_extractor=FakeMetadataExtractor(),
    )

    assert extraction.title == "soft shrimp tofu stew"
    assert extraction.description == "A simple side dish with shrimp and tofu."
    assert extraction.servings == 2
    assert extraction.cooking_time_minutes == 30
    assert extraction.kcal_per_serving == 220
    assert extraction.quality_score.estimated_fields == [
        "servings",
        "cooking_time_minutes",
        "kcal_per_serving",
    ]
    assert extraction.serving_weight_grams == 120
    assert extraction.protein_grams == 14
    assert extraction.sodium_milligrams == 99
    assert extraction.nutrition_source == "SOURCE"
    assert extraction.source_main_image_url == "https://example.com/large.jpg"
    assert extraction.ingredients[0].name == "tofu"
    assert extraction.ingredients[0].amount_text == "75g"
    assert extraction.ingredients[0].quantity == 75
    assert extraction.ingredients[0].unit == "g"
    assert extraction.steps[0].instruction == "Blanch the shrimp in boiling water."
    assert extraction.steps[0].source_image_url == "https://example.com/step.jpg"
    assert any(label.label_type == "CATEGORY" for label in extraction.labels)


def test_build_foodsafetykorea_extraction_uses_ai_difficulty_when_rule_is_ambiguous():
    calls = []

    def estimate(title, ingredients, steps):
        calls.append((title, ingredients, steps))
        return "normal"

    extraction = build_extraction(
        _row(step_count=5),
        ingredient_parser=IngredientParser([_ingredient(index) for index in range(6)]),
        text_rewriter=PassthroughTextRewriter(),
        difficulty_estimator=estimate,
        metadata_extractor=FakeMetadataExtractor(),
    )

    assert extraction.difficulty == "normal"
    assert len(calls) == 1


def test_build_foodsafetykorea_extraction_keeps_null_difficulty_when_ai_fails():
    extraction = build_extraction(
        _row(step_count=5),
        ingredient_parser=IngredientParser([_ingredient(index) for index in range(6)]),
        text_rewriter=PassthroughTextRewriter(),
        difficulty_estimator=lambda title, ingredients, steps: None,
        metadata_extractor=FakeMetadataExtractor(),
    )

    assert extraction.difficulty is None


def test_build_foodsafetykorea_extraction_fails_before_ai_when_ingredients_missing():
    with pytest.raises(ExtractionBuildError) as exc:
        build_extraction(
            _row(step_count=1),
            ingredient_parser=IngredientParser([]),
            text_rewriter=PassthroughTextRewriter(),
            difficulty_estimator=lambda *args: pytest.fail(
                "difficulty AI should not be called"
            ),
            metadata_extractor=FailingMetadataExtractor(),
        )

    assert exc.value.errors == [
        {"code": "MISSING_INGREDIENTS", "message": "ingredients are required."}
    ]


def test_build_foodsafetykorea_extraction_fails_before_ai_when_steps_missing():
    with pytest.raises(ExtractionBuildError) as exc:
        build_extraction(
            _row(step_count=0),
            ingredient_parser=IngredientParser([_ingredient(1)]),
            text_rewriter=PassthroughTextRewriter(),
            difficulty_estimator=lambda *args: pytest.fail(
                "difficulty AI should not be called"
            ),
            metadata_extractor=FailingMetadataExtractor(),
        )

    assert exc.value.errors == [
        {"code": "MISSING_STEPS", "message": "steps are required."}
    ]


def test_ai_metadata_extractor_returns_servings_and_total_time():
    agent = FakeMetadataAgent(
        RecipeMetadataOutput(
            servings=2.04,
            cooking_time_minutes=34,
        )
    )
    extractor = AIRecipeMetadataExtractor(agent=agent, model="test-model")

    metadata = extractor.extract(
        _row(step_count=2),
        "test recipe",
        [_ingredient(1)],
        [],
    )

    assert metadata.servings == 2.0
    assert metadata.cooking_time_minutes == 34
    assert '"title": "test recipe"' in agent.prompt


def test_validate_requires_servings_and_total_time():
    extraction = build_extraction(
        _row(step_count=1),
        ingredient_parser=IngredientParser([_ingredient(1)]),
        text_rewriter=PassthroughTextRewriter(),
        metadata_extractor=NullMetadataExtractor(),
    )

    errors = validate(extraction)

    assert {"code": "MISSING_SERVINGS", "message": "servings is required."} in errors
    assert {
        "code": "MISSING_COOKING_TIME",
        "message": "cooking_time_minutes is required.",
    } in errors
