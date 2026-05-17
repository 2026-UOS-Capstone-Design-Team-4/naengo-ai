from dataclasses import replace

from app.models.recipe import (
    RecipeIngredient,
    RecipeNutrition,
    RecipeQualityScore,
    RecipeStep,
)
from app.models.recipe_source import (
    RecipeSource,
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
    RecipeSourceQualityScore,
)
from app.services.ingestion.recipe_import_service import RecipeImportService
from app.services.ingestion.recipe_text_rewrite_service import draft_from_extraction


class FakeDb:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    def merge(self, item):
        self.added.append(item)
        return item

    def flush(self):
        pass


def test_import_helpers_write_rewritten_text_to_production_models():
    db = FakeDb()
    service = RecipeImportService(db)
    source = RecipeSource(
        source_id=1,
        source_type="WEB_SCRAPE",
        source_site="example",
        parser_type="HTML",
        raw_payload={},
        source_url="https://example.com/r/1",
        source_record_id="external-1",
        source_organization="Example Org",
        source_dataset_id="example-dataset",
        source_dataset_name="Example Dataset",
        source_license="CC BY",
        source_license_url="https://example.com/license",
    )
    extraction = RecipeSourceExtraction(
        title="원문 제목",
        description="원문 설명",
        servings=2,
        cooking_time_minutes=20,
        difficulty="easy",
        serving_weight_grams=250,
        carbohydrate_grams=12,
        protein_grams=8,
        fat_grams=4,
        sodium_milligrams=300,
        nutrition_source="SOURCE",
        nutrition_raw={"sodium": "300"},
    )
    extraction.ingredients = [
        RecipeSourceExtractedIngredient(
            name="김치",
            normalized_name="김치",
            amount_text="200g",
            raw_text="원문 재료 문장",
            sort_order=1,
        )
    ]
    extraction.steps = [
        RecipeSourceExtractedStep(
            step_no=1,
            instruction="원문 조리 문장",
            sort_order=1,
        )
    ]
    source.extraction = extraction

    draft = draft_from_extraction(extraction)
    draft = replace(
        draft,
        title="Naengo식 제목",
        description="Naengo식 설명",
        ingredients=[
            replace(
                draft.ingredients[0],
                raw_text="김치 200g",
            )
        ],
        steps=[
            replace(
                draft.steps[0],
                instruction="김치를 넣고 부드럽게 볶습니다.",
            )
        ],
    )

    recipe = service._create_recipe(source, draft)
    service._add_ingredients(recipe_id=10, draft=draft)
    service._add_steps(recipe_id=10, draft=draft)
    service._add_nutrition(recipe_id=10, extraction=extraction)

    ingredient = next(item for item in db.added if isinstance(item, RecipeIngredient))
    step = next(item for item in db.added if isinstance(item, RecipeStep))
    nutrition = next(item for item in db.added if isinstance(item, RecipeNutrition))

    assert recipe.title == "Naengo식 제목"
    assert recipe.description == "Naengo식 설명"
    assert recipe.source_id == 1
    assert recipe.cooking_time_minutes == 20
    assert ingredient.raw_text == "김치 200g"
    assert step.instruction == "김치를 넣고 부드럽게 볶습니다."
    assert nutrition.sodium_milligrams == 300
    assert nutrition.raw_payload == {"sodium": "300"}


def test_import_helpers_copy_source_quality_to_production_quality_score():
    db = FakeDb()
    service = RecipeImportService(db)
    extraction = RecipeSourceExtraction(
        title="source title",
        description="source description",
        servings=2,
        cooking_time_minutes=20,
        difficulty="easy",
    )
    extraction.quality_score = RecipeSourceQualityScore(
        completeness_score=0.92,
        nutrition_confidence=0.70,
        duplicate_score=0.10,
        reviewed_by=1,
    )

    service._add_quality_score(recipe_id=10, extraction=extraction)

    quality = next(item for item in db.added if isinstance(item, RecipeQualityScore))
    assert quality.recipe_id == 10
    assert quality.completeness_score == 0.92
    assert quality.nutrition_confidence == 0.70
    assert quality.duplicate_score == 0.10
    assert quality.reviewed_by == 1
    assert quality.classification_confidence is None
    assert quality.image_quality_score is None
    assert quality.instruction_quality_score is None
