from app.models.recipe import Recipe, RecipeIngredient, RecipeLabel, RecipeStep
from app.models.recipe_source import (
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedLabel,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
)
from app.services.ingestion.recipe_classification_service import (
    RecipeClassificationService,
    confidence_for_classification,
)


def make_extraction() -> RecipeSourceExtraction:
    extraction = RecipeSourceExtraction(
        title="김치두부찌개",
        summary="얼큰하게 끓이는 한식 찌개",
        description="김치와 두부를 넣고 끓입니다.",
        servings=2,
        cooking_time_minutes=20,
        difficulty="easy",
    )
    extraction.ingredients = [
        RecipeSourceExtractedIngredient(name="김치", normalized_name="김치"),
        RecipeSourceExtractedIngredient(name="두부", normalized_name="두부"),
        RecipeSourceExtractedIngredient(name="새우젓", normalized_name="새우젓"),
    ]
    extraction.steps = [
        RecipeSourceExtractedStep(
            step_no=1,
            instruction="냄비에 김치를 넣고 볶습니다.",
        ),
        RecipeSourceExtractedStep(
            step_no=2,
            instruction="물을 붓고 두부를 넣어 끓입니다.",
        ),
    ]
    extraction.labels = [
        RecipeSourceExtractedLabel(label_type="CATEGORY", label_value="찌개"),
        RecipeSourceExtractedLabel(label_type="TAG", label_value="얼큰한"),
    ]
    return extraction


def test_confidence_adds_evidence_bonus():
    result = confidence_for_classification(
        field="dish_type",
        source="AI",
        evidence_count=2,
        has_conflict=False,
    )

    assert result == 0.8


def test_confidence_caps_ai_sensitive_field():
    result = confidence_for_classification(
        field="diet_keywords",
        source="AI",
        evidence_count=3,
        has_conflict=False,
    )

    assert result == 0.65


def test_confidence_applies_conflict_penalty():
    result = confidence_for_classification(
        field="dish_type",
        source="RULE",
        evidence_count=2,
        has_conflict=True,
    )

    assert result == 0.7


def test_build_rule_classification_from_extraction():
    result = RecipeClassificationService().build_rule_classification(
        recipe_id=123,
        extraction=make_extraction(),
    )

    classification = result.classification
    assert classification.recipe_id == 123
    assert classification.dish_type == "stew"
    assert classification.main_ingredients == ["김치", "두부", "새우젓"]
    assert classification.cooking_methods == ["stir_fry", "boil"]
    assert classification.taste_keywords == ["spicy"]
    assert classification.allergen_keywords == ["새우", "대두"]
    assert classification.category_labels == ["찌개"]
    assert classification.classification_source == "RULE"
    assert classification.confidence_score is not None
    assert result.quality_score.classification_confidence == (
        classification.confidence_score
    )


def test_build_rule_classification_extracts_diet_and_texture_keywords():
    extraction = make_extraction()
    extraction.summary = "고단백 다이어트에 좋은 부드럽고 촉촉한 두부 요리"

    result = RecipeClassificationService().build_rule_classification(
        recipe_id=123,
        extraction=extraction,
    )

    classification = result.classification
    assert classification.diet_keywords == ["low_calorie", "high_protein"]
    assert classification.texture_keywords == ["soft", "moist"]


def test_build_from_recipe_uses_existing_recipe_tables():
    recipe = Recipe(
        recipe_id=77,
        title="김치볶음밥",
        summary="매운 한 그릇 볶음밥",
        description="김치와 밥을 넣어 볶습니다.",
        servings=1,
        cooking_time_minutes=15,
        difficulty="easy",
    )
    recipe.ingredients_list = [
        RecipeIngredient(name="김치", normalized_name="김치"),
        RecipeIngredient(name="밥", normalized_name="밥"),
        RecipeIngredient(name="달걀", normalized_name="달걀"),
    ]
    recipe.steps = [
        RecipeStep(step_no=1, instruction="팬에 김치와 밥을 넣고 볶습니다."),
    ]
    recipe.labels = [
        RecipeLabel(label_type="CATEGORY", label_value="밥/덮밥"),
    ]

    result = RecipeClassificationService().build_from_recipe(recipe)

    classification = result.classification
    assert classification.recipe_id == 77
    assert classification.dish_type == "fried_rice"
    assert classification.main_ingredients == ["김치", "밥", "달걀"]
    assert classification.cooking_methods == ["stir_fry"]
    assert classification.taste_keywords == ["spicy"]
    assert classification.allergen_keywords == ["달걀"]


def test_validate_classification_requires_review_when_confidence_missing():
    extraction = RecipeSourceExtraction(
        title="알 수 없는 요리",
        summary=None,
        description="분류 단서가 거의 없습니다.",
        servings=1,
        cooking_time_minutes=10,
        difficulty="easy",
    )
    extraction.ingredients = []
    extraction.steps = []
    extraction.labels = []

    errors = RecipeClassificationService().validate_extraction_classification(
        extraction
    )

    assert errors == [
        {
            "code": "CLASSIFICATION_CONFIDENCE_MISSING",
            "message": "추천/검색 분류값을 충분히 생성하지 못했습니다.",
        }
    ]
