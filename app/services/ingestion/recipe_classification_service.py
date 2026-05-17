import re
from dataclasses import dataclass
from typing import Any

from app.models.recipe import Recipe, RecipeClassification, RecipeQualityScore
from app.models.recipe_source import RecipeSourceExtraction

_SENSITIVE_FIELDS = {"allergen_keywords", "diet_keywords"}
_SOURCE_BASE_SCORE = {
    "RULE": 0.85,
    "AI": 0.70,
    "ADMIN": 1.0,
}
_REVIEW_REQUIRED_THRESHOLD = 0.60

_COOKING_METHOD_KEYWORDS = {
    "stir_fry": ["볶", "팬에", "프라이팬"],
    "boil": ["끓", "삶", "데치"],
    "grill": ["굽", "구워"],
    "steam": ["찌", "찜"],
    "fry": ["튀기"],
    "mix": ["무치", "버무", "섞"],
}
_EQUIPMENT_KEYWORDS = {
    "air_fryer": ["에어프라이어"],
    "microwave": ["전자레인지", "렌지"],
    "oven": ["오븐"],
    "blender": ["믹서", "블렌더"],
}
_ALLERGEN_KEYWORDS = {
    "새우": ["새우", "shrimp"],
    "게": ["게", "crab"],
    "우유": ["우유", "milk", "치즈", "버터", "크림"],
    "달걀": ["달걀", "계란", "egg"],
    "땅콩": ["땅콩", "peanut"],
    "밀": ["밀가루", "flour", "면", "파스타"],
    "대두": ["두부", "된장", "간장", "콩"],
}
_DISH_TYPE_KEYWORDS = {
    "stew": ["찌개", "전골"],
    "soup": ["국", "탕"],
    "fried_rice": ["볶음밥"],
    "stir_fry": ["볶음"],
    "side_dish": ["반찬", "무침"],
    "salad": ["샐러드"],
}
_TASTE_KEYWORDS = {
    "spicy": ["매운", "얼큰", "칼칼", "고춧가루", "고추장", "청양고추"],
    "savory": ["고소", "담백", "감칠맛", "구수"],
    "sweet": ["달콤", "달달", "설탕", "꿀", "올리고당"],
    "sour": ["새콤", "식초", "레몬", "라임"],
    "salty": ["짭짤", "간장", "소금"],
}
_TEXTURE_KEYWORDS = {
    "crispy": ["바삭", "크리스피"],
    "soft": ["부드", "말랑"],
    "chewy": ["쫄깃", "쫀득"],
    "moist": ["촉촉"],
}
_DIET_KEYWORDS = {
    "vegan": ["비건"],
    "vegetarian": ["채식"],
    "low_calorie": ["저칼로리", "다이어트"],
    "low_carb": ["저탄수", "저탄고지"],
    "high_protein": ["고단백", "단백질"],
    "gluten_free": ["글루텐프리", "무글루텐"],
}


@dataclass(frozen=True)
class ClassificationBuildResult:
    classification: RecipeClassification
    quality_score: RecipeQualityScore
    review_required: bool = False
    review_reasons: list[dict] | None = None


@dataclass(frozen=True)
class ClassificationInput:
    title: str | None
    summary: str | None
    description: str | None
    ingredients: list[str]
    steps: list[str]
    category_labels: list[str]
    labels: list[str]


def confidence_for_classification(
    field: str,
    source: str,
    evidence_count: int,
    has_conflict: bool,
) -> float:
    base = _SOURCE_BASE_SCORE[source]
    score = base + min(evidence_count, 3) * 0.05

    if field in _SENSITIVE_FIELDS and source == "AI":
        score = min(score, 0.65)

    if has_conflict:
        score -= 0.25

    return round(max(0.0, min(score, 1.0)), 2)


class RecipeClassificationService:
    def build_rule_classification(
        self,
        recipe_id: int,
        extraction: RecipeSourceExtraction,
    ) -> ClassificationBuildResult:
        return self.build_from_input(recipe_id, _input_from_extraction(extraction))

    def build_from_recipe(self, recipe: Recipe) -> ClassificationBuildResult:
        return self.build_from_input(recipe.recipe_id, _input_from_recipe(recipe))

    def build_from_input(
        self,
        recipe_id: int,
        data: ClassificationInput,
    ) -> ClassificationBuildResult:
        text = _build_input_text(data)
        steps_text = " ".join(data.steps)
        main_ingredients = data.ingredients[:5]
        cooking_methods = _match_keyword_map(steps_text, _COOKING_METHOD_KEYWORDS)
        equipment = _match_keyword_map(steps_text, _EQUIPMENT_KEYWORDS)
        allergen_keywords = _match_allergens(data.ingredients)
        dish_type = _infer_dish_type(data.title, data.category_labels)
        taste_keywords = _match_keyword_map(text, _TASTE_KEYWORDS)
        texture_keywords = _match_keyword_map(text, _TEXTURE_KEYWORDS)
        diet_keywords = _match_keyword_map(text, _DIET_KEYWORDS)

        field_scores = [
            _score_if_present(
                "main_ingredients",
                main_ingredients,
                len(data.ingredients),
            ),
            _score_if_present(
                "cooking_methods",
                cooking_methods,
                len(cooking_methods),
            ),
            _score_if_present("equipment", equipment, len(equipment)),
            _score_if_present(
                "allergen_keywords",
                allergen_keywords,
                len(allergen_keywords),
            ),
            _score_if_present(
                "category_labels",
                data.category_labels,
                len(data.category_labels),
            ),
            _score_if_present("dish_type", [dish_type] if dish_type else [], 1),
            _score_if_present("taste_keywords", taste_keywords, len(taste_keywords)),
            _score_if_present(
                "texture_keywords",
                texture_keywords,
                len(texture_keywords),
            ),
            _score_if_present("diet_keywords", diet_keywords, len(diet_keywords)),
        ]
        confidence = _aggregate_scores([score for score in field_scores if score])
        review_reasons = _build_review_reasons(confidence)

        classification = RecipeClassification(
            recipe_id=recipe_id,
            dish_type=dish_type,
            cooking_methods=cooking_methods,
            meal_types=[],
            occasions=[],
            situations=[],
            main_ingredients=main_ingredients,
            taste_keywords=taste_keywords,
            texture_keywords=texture_keywords,
            diet_keywords=diet_keywords,
            allergen_keywords=allergen_keywords,
            equipment=equipment,
            season=[],
            category_labels=data.category_labels,
            classification_source="RULE",
            confidence_score=confidence,
        )
        quality_score = RecipeQualityScore(
            recipe_id=recipe_id,
            classification_confidence=confidence,
        )
        return ClassificationBuildResult(
            classification=classification,
            quality_score=quality_score,
            review_required=bool(review_reasons),
            review_reasons=review_reasons,
        )

    def validate_extraction_classification(
        self,
        extraction: RecipeSourceExtraction,
    ) -> list[dict]:
        result = self.build_rule_classification(recipe_id=0, extraction=extraction)
        return result.review_reasons or []


recipe_classification_service = RecipeClassificationService()


def _input_from_extraction(extraction: RecipeSourceExtraction) -> ClassificationInput:
    category_labels = _labels_by_type(extraction, "CATEGORY")
    labels = [label.label_value for label in extraction.labels]
    return ClassificationInput(
        title=extraction.title,
        summary=extraction.summary,
        description=extraction.description,
        ingredients=_ingredient_names(extraction),
        steps=[step.instruction for step in extraction.steps],
        category_labels=category_labels,
        labels=labels,
    )


def _input_from_recipe(recipe: Recipe) -> ClassificationInput:
    ingredients = []
    for ingredient in recipe.ingredients_list:
        name = ingredient.normalized_name or ingredient.name
        if name and name not in ingredients:
            ingredients.append(name)

    category_labels = [
        label.label_value
        for label in recipe.labels
        if label.label_type == "CATEGORY"
    ]
    labels = [label.label_value for label in recipe.labels]
    return ClassificationInput(
        title=recipe.title,
        summary=recipe.summary,
        description=recipe.description,
        ingredients=ingredients,
        steps=[step.instruction for step in recipe.steps],
        category_labels=category_labels,
        labels=labels,
    )


def _build_input_text(data: ClassificationInput) -> str:
    ingredients = " ".join(data.ingredients)
    labels = " ".join(data.labels)
    return " ".join(
        part
        for part in [
            data.title,
            data.summary,
            data.description,
            ingredients,
            labels,
            " ".join(data.steps),
        ]
        if part
    )


def _ingredient_names(extraction: RecipeSourceExtraction) -> list[str]:
    values = []
    for ingredient in extraction.ingredients:
        name = ingredient.normalized_name or ingredient.name
        if name and name not in values:
            values.append(name)
    return values


def _labels_by_type(extraction: RecipeSourceExtraction, label_type: str) -> list[str]:
    values = []
    for label in extraction.labels:
        if label.label_type == label_type and label.label_value not in values:
            values.append(label.label_value)
    return values


def _match_keyword_map(text: str, keyword_map: dict[str, list[str]]) -> list[str]:
    return [
        value
        for value, keywords in keyword_map.items()
        if any(keyword in text for keyword in keywords)
    ]


def _match_allergens(ingredients: list[str]) -> list[str]:
    text = " ".join(ingredients).lower()
    return [
        allergen
        for allergen, keywords in _ALLERGEN_KEYWORDS.items()
        if any(keyword.lower() in text for keyword in keywords)
    ]


def _infer_dish_type(title: str | None, category_labels: list[str]) -> str | None:
    text = " ".join(part for part in [title, *category_labels] if part)
    for dish_type, keywords in _DISH_TYPE_KEYWORDS.items():
        if any(re.search(keyword, text) for keyword in keywords):
            return dish_type
    return None


def _score_if_present(
    field: str,
    values: list[Any],
    evidence_count: int,
) -> float | None:
    if not values:
        return None
    return confidence_for_classification(
        field=field,
        source="RULE",
        evidence_count=evidence_count,
        has_conflict=False,
    )


def _aggregate_scores(scores: list[float]) -> float | None:
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def _build_review_reasons(confidence: float | None) -> list[dict]:
    if confidence is None:
        return [
            {
                "code": "CLASSIFICATION_CONFIDENCE_MISSING",
                "message": "추천/검색 분류값을 충분히 생성하지 못했습니다.",
            }
        ]
    if confidence < _REVIEW_REQUIRED_THRESHOLD:
        return [
            {
                "code": "CLASSIFICATION_CONFIDENCE_LOW",
                "message": (
                    "추천/검색 분류 신뢰도가 낮습니다: "
                    f"{confidence:.2f}"
                ),
            }
        ]
    return []
