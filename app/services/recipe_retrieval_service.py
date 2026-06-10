import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import exists, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import (
    Recipe,
    RecipeClassification,
    RecipeEmbedding,
    RecipeIngredient,
)
from app.models.recipe_source import RecipeSource  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.embedding_service import EmbeddingService, embedding_service
from app.services.personalization_taxonomy import (
    canonical_aliases,
    canonicalize_diet_keywords,
    canonicalize_taste_keywords,
)

DEFAULT_DIFFICULTY_BONUS = {
    "easy": 1.5,
    "normal": 0.5,
    "hard": 0.0,
}
AVAILABLE_INGREDIENT_BONUS = 0.5
REQUESTED_DIFFICULTY_BONUS = 1.2
EXACT_DISH_TITLE_BONUS = 4.0
PARTIAL_DISH_TITLE_BONUS = 2.0
MAIN_INGREDIENT_EXACT_BONUS = 1.5
MAIN_INGREDIENT_VARIANT_BONUS = 1.0
MAIN_INGREDIENT_SUBSTRING_BONUS = 0.5
AVAILABLE_INGREDIENT_VARIANT_BONUS = 0.25
ALL_MAIN_INGREDIENTS_BONUS = 2.0
MAIN_INGREDIENT_MATCH_RATIO_BONUS = 1.0
PREFERRED_INGREDIENT_BONUS = 0.6
DISLIKED_INGREDIENT_PENALTY = 8.0
SKILL_DIFFICULTY_BONUS = 0.8
TIME_PREFERENCE_PENALTY = 0.8
_INGREDIENT_SYNONYMS = {
    "계란": {"달걀"},
    "달걀": {"계란"},
    "파": {"대파", "쪽파"},
    "대파": {"파", "쪽파"},
    "쪽파": {"파", "대파"},
    "새우": {"칵테일새우", "흰다리새우"},
    "칵테일새우": {"새우", "흰다리새우"},
    "흰다리새우": {"새우", "칵테일새우"},
    "삼겹살": {"돼지고기", "돼지삼겹살", "대패삼겹살"},
    "돼지삼겹살": {"삼겹살", "돼지고기", "대패삼겹살"},
    "대패삼겹살": {"삼겹살", "돼지고기", "돼지삼겹살"},
    "미나리": {"돌미나리", "참미나리"},
    "돌미나리": {"미나리", "참미나리"},
    "참미나리": {"미나리", "돌미나리"},
}

logger = logging.getLogger(__name__)


class RecipeRetrievalService:
    def __init__(
        self,
        embedder: EmbeddingService,
        session_factory: Callable[[], Session],
    ):
        self.embedder = embedder
        self.session_factory = session_factory

    def search_recipes(
        self,
        query: str,
        limit: int = 3,
        score_cutoff: float = 0.65,
        plan: Any | None = None,
    ) -> list[Recipe]:
        db = self.session_factory()
        try:
            query_vector = self.embedder.embed_query(query)
            recipes = self._search_once(
                db,
                query_vector,
                limit=limit,
                score_cutoff=score_cutoff,
                plan=plan,
            )
            if recipes or plan is None:
                return recipes

            fallback_plan = _hard_constraint_fallback_plan(plan)
            return self._search_once(
                db,
                query_vector,
                limit=limit,
                score_cutoff=score_cutoff,
                plan=fallback_plan,
            )
        finally:
            db.close()

    def _search_once(
        self,
        db: Session,
        query_vector: list[float],
        limit: int,
        score_cutoff: float,
        plan: Any | None,
    ) -> list[Recipe]:
        dist_expr = RecipeEmbedding.embedding.cosine_distance(query_vector)
        candidate_limit = _candidate_limit(limit, plan)
        base_filters = [
            Recipe.is_active.is_(True),
            RecipeEmbedding.embedding_type == "RECIPE_SEARCH",
            dist_expr < score_cutoff,
        ]
        hard_filters = _hard_filters(plan)
        if logger.isEnabledFor(logging.INFO):
            embedding_candidates = _count_candidates(db, base_filters)
            filtered_candidates = _count_candidates(
                db,
                [*base_filters, *hard_filters],
            )
            logger.info(
                "RAG 후보 수: embedding=%d hard_filtered=%d candidate_limit=%d",
                embedding_candidates,
                filtered_candidates,
                candidate_limit,
            )

        stmt = (
            select(Recipe, dist_expr.label("distance"))
            .join(RecipeEmbedding, Recipe.recipe_id == RecipeEmbedding.recipe_id)
            .where(*base_filters, *hard_filters)
            .options(
                selectinload(Recipe.ingredients_list),
                selectinload(Recipe.steps),
                selectinload(Recipe.labels),
                selectinload(Recipe.stats),
                selectinload(Recipe.classifications),
            )
            .order_by(dist_expr)
            .limit(candidate_limit)
        )
        rows = db.execute(stmt).all()
        recipes = [row[0] for row in rows]
        distances = {row[0].recipe_id: float(row[1]) for row in rows}
        if plan is None:
            logger.info("RAG 반환 수: final=%d", len(recipes))
            _log_ranked_candidates(recipes, distances, plan=None, limit=limit)
            return recipes
        lexical_recipes = _lexical_candidates(
            db,
            plan,
            hard_filters=hard_filters,
            candidate_limit=candidate_limit,
        )
        recipes = _merge_recipes(recipes, lexical_recipes)
        reranked = _rerank_recipes(recipes, plan)[:limit]
        logger.info(
            "RAG 반환 수: before_rerank=%d final=%d",
            len(recipes),
            len(reranked),
        )
        _log_ranked_candidates(reranked, distances, plan=plan, limit=limit)
        return reranked

    def recipe_to_payload(
        self,
        recipe: Recipe,
        liked_ids: set[int] | None = None,
        scrapped_ids: set[int] | None = None,
    ) -> dict:
        return {
            "id": recipe.recipe_id,
            "title": recipe.title,
            "summary": recipe.summary,
            "description": recipe.description,
            "servings": float(recipe.servings) if recipe.servings else None,
            "cooking_time_minutes": recipe.cooking_time_minutes,
            "kcal_per_serving": recipe.kcal_per_serving,
            "difficulty": recipe.difficulty,
            "author_type": recipe.author_type,
            "main_image_url": recipe.main_image_url,
            "source_url": recipe.source_url,
            "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
            "category": recipe.category,
            "tags": recipe.tags,
            "tips": recipe.tips,
            "warnings": recipe.warnings,
            "ingredients": recipe.ingredients,
            "steps": [
                {
                    "step_no": step.step_no,
                    "instruction": step.instruction,
                    "image_url": step.image_url,
                    "tip": step.tip,
                }
                for step in recipe.steps
            ],
            "likes_count": recipe.stats.likes_count if recipe.stats else 0,
            "scrap_count": recipe.stats.scrap_count if recipe.stats else 0,
            "is_liked": recipe.recipe_id in (liked_ids or set()),
            "is_scrapped": recipe.recipe_id in (scrapped_ids or set()),
            "_diet_keywords": (
                list(recipe.classifications.diet_keywords or [])
                if recipe.classifications
                else []
            ),
            "_taste_keywords": (
                list(recipe.classifications.taste_keywords or [])
                if recipe.classifications
                else []
            ),
            "_category_labels": (
                list(recipe.classifications.category_labels or [])
                if recipe.classifications
                else []
            ),
        }


recipe_retrieval_service = RecipeRetrievalService(
    embedder=embedding_service,
    session_factory=SessionLocal,
)


def _hard_constraint_fallback_plan(plan: Any | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "target_dish_name": None,
        "available_ingredients": [],
        "main_ingredients": [],
        "required_ingredients": _plan_list(plan, "required_ingredients"),
        "avoid_ingredients": _plan_list(plan, "avoid_ingredients"),
        "allergies": _plan_list(plan, "allergies"),
        "hard_diet_keywords": _plan_list(plan, "hard_diet_keywords"),
        "cooking_time_max": _positive_int(_plan_value(plan, "cooking_time_max")),
        "difficulty": None,
        "cooking_skill": None,
        "preferred_cooking_time_minutes": None,
        "preferred_ingredients": [],
        "disliked_ingredients": _plan_list(plan, "disliked_ingredients"),
        "taste_keywords": [],
        "diet_keywords": [],
        "preferred_categories": [],
        "dish_type": None,
        "cuisine_type": None,
        "cooking_method": None,
        "servings": None,
    }


def _hard_filters(plan: Any | None) -> list:
    if plan is None:
        return []

    filters = []
    cooking_time_max = _positive_int(_plan_value(plan, "cooking_time_max"))
    if cooking_time_max is not None:
        filters.append(Recipe.cooking_time_minutes <= cooking_time_max)

    for ingredient in _plan_list(plan, "required_ingredients"):
        filters.append(_ingredient_exists(ingredient))

    avoid_ingredients = _plan_list(plan, "avoid_ingredients")
    avoid_ingredients.extend(_plan_list(plan, "allergies"))
    if avoid_ingredients:
        avoid_filters = [
            _ingredient_exists(ingredient) for ingredient in avoid_ingredients
        ]
        filters.append(not_(or_(*avoid_filters)))

    for keyword in canonicalize_diet_keywords(
        _plan_list(plan, "hard_diet_keywords")
    ):
        filters.append(
            exists().where(
                RecipeClassification.recipe_id == Recipe.recipe_id,
                RecipeClassification.diet_keywords.contains([keyword]),
            )
        )

    return filters


def _ingredient_exists(ingredient: str):
    values = _ingredient_variants(ingredient)
    return exists().where(
        RecipeIngredient.recipe_id == Recipe.recipe_id,
        or_(*[
            predicate
            for value in values
            for predicate in (
                RecipeIngredient.normalized_name.ilike(value),
                RecipeIngredient.name.ilike(value),
            )
        ]),
    )


def _lexical_candidates(
    db: Session,
    plan: Any,
    hard_filters: list,
    candidate_limit: int,
) -> list[Recipe]:
    lexical_filters = _lexical_filters(plan)
    if not lexical_filters:
        return []
    stmt = (
        select(Recipe)
        .where(
            Recipe.is_active.is_(True),
            *hard_filters,
            or_(*lexical_filters),
        )
        .options(
            selectinload(Recipe.ingredients_list),
            selectinload(Recipe.steps),
            selectinload(Recipe.labels),
            selectinload(Recipe.stats),
            selectinload(Recipe.classifications),
        )
        .limit(candidate_limit)
    )
    return list(db.execute(stmt).scalars())


def _lexical_filters(plan: Any) -> list:
    filters = []
    target_dish_name = _clean_text(_plan_value(plan, "target_dish_name"))
    if target_dish_name:
        filters.append(Recipe.title.ilike(f"%{target_dish_name}%"))
    ingredients = [
        *_plan_list(plan, "main_ingredients"),
        *_plan_list(plan, "available_ingredients"),
        *_plan_list(plan, "required_ingredients"),
    ]
    for ingredient in ingredients:
        filters.append(_ingredient_exists(ingredient))
    return filters


def _merge_recipes(primary: list[Recipe], secondary: list[Recipe]) -> list[Recipe]:
    seen = set()
    merged = []
    for recipe in [*primary, *secondary]:
        if recipe.recipe_id in seen:
            continue
        merged.append(recipe)
        seen.add(recipe.recipe_id)
    return merged


def _rerank_recipes(recipes: list[Recipe], plan: Any) -> list[Recipe]:
    return sorted(
        recipes,
        key=lambda recipe: _plan_bonus(recipe, plan),
        reverse=True,
    )


def _plan_bonus(recipe: Recipe, plan: Any) -> float:
    score = 0.0
    target_dish_name = _clean_text(_plan_value(plan, "target_dish_name"))
    if target_dish_name:
        recipe_title = _clean_text(recipe.title) or ""
        if _normalize_for_match(target_dish_name) == _normalize_for_match(recipe_title):
            score += EXACT_DISH_TITLE_BONUS
        elif _contains_normalized(recipe_title, target_dish_name):
            score += PARTIAL_DISH_TITLE_BONUS

    ingredient_values = _recipe_ingredient_values(recipe)

    main_ingredients = _plan_list(plan, "main_ingredients")
    main_match_count = _ingredient_match_count(ingredient_values, main_ingredients)
    if main_ingredients:
        score += sum(
            _main_ingredient_bonus(ingredient_values, value)
            for value in main_ingredients
        )
        score += (
            main_match_count / len(main_ingredients)
        ) * MAIN_INGREDIENT_MATCH_RATIO_BONUS
        if main_match_count == len(main_ingredients):
            score += ALL_MAIN_INGREDIENTS_BONUS

    for value in _plan_list(plan, "available_ingredients"):
        score += _available_ingredient_bonus(ingredient_values, value)

    for value in _plan_list(plan, "required_ingredients"):
        if _ingredient_match_strength(ingredient_values, value) in {"exact", "variant"}:
            score += 2.0

    for value in _plan_list(plan, "preferred_ingredients"):
        score += _available_ingredient_bonus(ingredient_values, value)
        if _ingredient_match_strength(ingredient_values, value):
            score += PREFERRED_INGREDIENT_BONUS

    for value in _plan_list(plan, "disliked_ingredients"):
        if _ingredient_match_strength(ingredient_values, value):
            score -= DISLIKED_INGREDIENT_PENALTY

    difficulty = _clean_text(_plan_value(plan, "difficulty"))
    if difficulty:
        if difficulty == recipe.difficulty:
            score += REQUESTED_DIFFICULTY_BONUS
    else:
        score += DEFAULT_DIFFICULTY_BONUS.get(recipe.difficulty, 0.0)
    cooking_skill = _clean_text(_plan_value(plan, "cooking_skill"))
    if cooking_skill and cooking_skill == recipe.difficulty:
        score += SKILL_DIFFICULTY_BONUS

    preferred_time = _positive_int(
        _plan_value(plan, "preferred_cooking_time_minutes")
    )
    if (
        preferred_time is not None
        and recipe.cooking_time_minutes is not None
        and recipe.cooking_time_minutes > preferred_time
    ):
        score -= TIME_PREFERENCE_PENALTY

    classification = recipe.classifications
    if classification is not None:
        score += _overlap_score(
            canonicalize_taste_keywords(_plan_list(plan, "taste_keywords")),
            classification.taste_keywords or [],
            weight=0.5,
        )
        score += _overlap_score(
            canonicalize_diet_keywords(_plan_list(plan, "diet_keywords")),
            classification.diet_keywords or [],
            weight=0.75,
        )
        dish_type = _clean_text(_plan_value(plan, "dish_type"))
        if dish_type and dish_type == classification.dish_type:
            score += 1.0
        cuisine_type = _clean_text(_plan_value(plan, "cuisine_type"))
        if cuisine_type and cuisine_type == classification.cuisine_type:
            score += 0.75
        cooking_method = _clean_text(_plan_value(plan, "cooking_method"))
        if cooking_method and cooking_method in (classification.cooking_methods or []):
            score += 0.75
        score += _overlap_score(
            _plan_list(plan, "preferred_categories"),
            classification.category_labels or [],
            weight=0.75,
        )

    servings = _positive_int(_plan_value(plan, "servings"))
    if servings is not None and recipe.servings is not None:
        try:
            diff = abs(float(recipe.servings) - servings)
        except (TypeError, ValueError):
            diff = 99
        if diff == 0:
            score += 0.5
        elif diff <= 1:
            score += 0.25

    return score


def _log_ranked_candidates(
    recipes: list[Recipe],
    distances: dict[int, float],
    plan: Any | None,
    limit: int,
) -> None:
    if not logger.isEnabledFor(logging.INFO):
        return
    payload = [
        _candidate_debug_payload(recipe, distances.get(recipe.recipe_id), plan)
        for recipe in recipes[:limit]
    ]
    logger.info("RAG 최종 후보: %s", payload)


def _candidate_debug_payload(
    recipe: Recipe,
    distance: float | None,
    plan: Any | None,
) -> dict[str, Any]:
    ingredient_values = _recipe_ingredient_values(recipe)
    classification = recipe.classifications
    return {
        "recipe_id": recipe.recipe_id,
        "title": recipe.title,
        "distance": round(distance, 4) if distance is not None else None,
        "bonus": round(_plan_bonus(recipe, plan), 3) if plan is not None else None,
        "difficulty": recipe.difficulty,
        "target_dish_name": _clean_text(_plan_value(plan, "target_dish_name")),
        "title_match": _title_match_type(recipe, plan),
        "main_matches": _matched_ingredients(
            ingredient_values,
            _plan_list(plan, "main_ingredients"),
        ),
        "available_matches": _matched_ingredients(
            ingredient_values,
            _plan_list(plan, "available_ingredients"),
        ),
        "preferred_matches": _matched_ingredients(
            ingredient_values,
            _plan_list(plan, "preferred_ingredients"),
        ),
        "disliked_matches": _matched_ingredients(
            ingredient_values,
            _plan_list(plan, "disliked_ingredients"),
        ),
        "required_matches": _matched_ingredients(
            ingredient_values,
            _plan_list(plan, "required_ingredients"),
        ),
        "taste_matches": _matched_values(
            _plan_list(plan, "taste_keywords"),
            classification.taste_keywords if classification is not None else [],
        ),
        "diet_matches": _matched_values(
            _plan_list(plan, "diet_keywords"),
            classification.diet_keywords if classification is not None else [],
        ),
    }


def _overlap_score(wanted: list[str], actual: list[str], weight: float) -> float:
    actual_set = set(actual)
    return sum(weight for value in wanted if value in actual_set)


def _plan_value(plan: Any, field: str) -> Any:
    if isinstance(plan, dict):
        return plan.get(field)
    return getattr(plan, field, None)


def _plan_list(plan: Any, field: str) -> list[str]:
    value = _plan_value(plan, field)
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _contains_normalized(text: str, query: str) -> bool:
    normalized_text = _normalize_for_match(text)
    normalized_query = _normalize_for_match(query)
    return bool(normalized_query and normalized_query in normalized_text)


def _title_match_type(recipe: Recipe, plan: Any | None) -> str | None:
    target_dish_name = _clean_text(_plan_value(plan, "target_dish_name"))
    if not target_dish_name:
        return None
    recipe_title = _clean_text(recipe.title) or ""
    if _normalize_for_match(target_dish_name) == _normalize_for_match(recipe_title):
        return "exact"
    if _contains_normalized(recipe_title, target_dish_name):
        return "partial"
    return None


def _normalize_for_match(value: str) -> str:
    return "".join(str(value).lower().split())


def _ingredient_match_strength(
    ingredient_values: set[str],
    query: str,
) -> str | None:
    normalized_values = {_normalize_for_match(value) for value in ingredient_values}
    normalized_query = _normalize_for_match(query)
    if normalized_query in normalized_values:
        return "exact"

    normalized_variants = {
        _normalize_for_match(value)
        for value in _ingredient_variants(query)
        if _normalize_for_match(value) != normalized_query
    }
    if normalized_values.intersection(normalized_variants):
        return "variant"

    if any(normalized_query in value for value in normalized_values):
        return "substring"
    return None


def _main_ingredient_bonus(ingredient_values: set[str], query: str) -> float:
    strength = _ingredient_match_strength(ingredient_values, query)
    if strength == "exact":
        return MAIN_INGREDIENT_EXACT_BONUS
    if strength == "variant":
        return MAIN_INGREDIENT_VARIANT_BONUS
    if strength == "substring":
        return MAIN_INGREDIENT_SUBSTRING_BONUS
    return 0.0


def _available_ingredient_bonus(ingredient_values: set[str], query: str) -> float:
    strength = _ingredient_match_strength(ingredient_values, query)
    if strength == "exact":
        return AVAILABLE_INGREDIENT_BONUS
    if strength == "variant":
        return AVAILABLE_INGREDIENT_VARIANT_BONUS
    return 0.0


def _matched_ingredients(ingredient_values: set[str], queries: list[str]) -> list[dict]:
    return [
        {"value": query, "match": strength}
        for query in queries
        if (strength := _ingredient_match_strength(ingredient_values, query))
    ]


def _ingredient_match_count(ingredient_values: set[str], queries: list[str]) -> int:
    return sum(
        1 for query in queries if _ingredient_match_strength(ingredient_values, query)
    )


def _matched_values(wanted: list[str], actual: list[str]) -> list[str]:
    actual_set = set(actual)
    return [value for value in wanted if value in actual_set]


def _recipe_ingredient_values(recipe: Recipe) -> set[str]:
    return {
        (item.normalized_name or item.name or "").strip()
        for item in recipe.ingredients_list
        if (item.normalized_name or item.name)
    }


def _ingredient_variants(value: str) -> set[str]:
    text = _clean_text(value)
    if text is None:
        return set()
    variants = {text}
    variants.update(_INGREDIENT_SYNONYMS.get(text, set()))
    variants.update(canonical_aliases("allergies", text))
    return variants


def _count_candidates(db: Session, filters: list) -> int:
    stmt = (
        select(func.count())
        .select_from(Recipe)
        .join(RecipeEmbedding, Recipe.recipe_id == RecipeEmbedding.recipe_id)
        .where(*filters)
    )
    return int(db.execute(stmt).scalar() or 0)


def _candidate_limit(limit: int, plan: Any | None) -> int:
    if plan is None:
        return limit
    if len(_plan_list(plan, "main_ingredients")) >= 2:
        return max(limit * 10, 30)
    return max(limit * 5, 10)


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
