import base64
import binascii
import json
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.recipe import Recipe, RecipeStats
from app.models.recipe_source import RecipeSource


class AdminRecipeNotFoundError(Exception):
    pass


class AdminRecipeInvalidCursorError(ValueError):
    pass


class AdminRecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_recipes(
        self,
        *,
        sort: str = "latest",
        cursor: str | None = None,
        limit: int = 20,
        is_active: bool | None = None,
        source_site: str | None = None,
        author_type: str | None = None,
        visibility: str | None = None,
        difficulty: str | None = None,
        q: str | None = None,
    ) -> tuple[list[Recipe], str | None]:
        stmt = (
            select(Recipe)
            .options(
                joinedload(Recipe.stats),
                joinedload(Recipe.nutrition),
                joinedload(Recipe.classifications),
                selectinload(Recipe.embeddings),
                joinedload(Recipe.source),
            )
            .limit(limit + 1)
        )
        if is_active is not None:
            stmt = stmt.where(Recipe.is_active.is_(is_active))
        if source_site:
            stmt = stmt.join(
                RecipeSource,
                Recipe.source_id == RecipeSource.source_id,
            ).where(RecipeSource.source_site == source_site)
        if author_type:
            stmt = stmt.where(Recipe.author_type == author_type)
        if visibility:
            stmt = stmt.where(Recipe.visibility == visibility)
        if difficulty:
            stmt = stmt.where(Recipe.difficulty == difficulty)
        if q:
            stmt = stmt.where(Recipe.title.ilike(f"%{q}%"))

        if sort == "likes":
            stmt = self._apply_count_sort(
                stmt,
                sort,
                cursor,
                func.coalesce(RecipeStats.likes_count, 0),
            )
        elif sort == "scraps":
            stmt = self._apply_count_sort(
                stmt,
                sort,
                cursor,
                func.coalesce(RecipeStats.scrap_count, 0),
            )
        else:
            cursor_payload = _decode_cursor(cursor) if cursor else None
            if cursor_payload and cursor_payload.get("sort") != sort:
                raise AdminRecipeInvalidCursorError("Cursor sort mismatch.")
            cursor_id = (
                _cursor_recipe_id(cursor_payload) if cursor_payload else None
            )
            if cursor_id is not None:
                stmt = stmt.where(Recipe.recipe_id < cursor_id)
            stmt = stmt.order_by(Recipe.recipe_id.desc())

        recipes = list(self.db.execute(stmt).scalars().unique().all())
        has_next = len(recipes) > limit
        items = recipes[:limit]
        next_cursor = (
            self._build_next_cursor(sort, items[-1]) if has_next and items else None
        )
        return items, next_cursor

    def _apply_count_sort(self, stmt, sort: str, cursor: str | None, count_expr):
        stmt = stmt.outerjoin(RecipeStats, Recipe.recipe_id == RecipeStats.recipe_id)
        if cursor:
            cursor_count, cursor_id = _parse_count_cursor(cursor, sort)
            stmt = stmt.where(
                or_(
                    count_expr < cursor_count,
                    and_(count_expr == cursor_count, Recipe.recipe_id < cursor_id),
                )
            )
        return stmt.order_by(count_expr.desc(), Recipe.recipe_id.desc())

    def _build_next_cursor(self, sort: str, recipe: Recipe) -> str:
        payload: dict[str, Any] = {
            "sort": sort,
            "recipe_id": recipe.recipe_id,
        }
        if sort == "likes":
            payload["count"] = recipe.stats.likes_count if recipe.stats else 0
            return _encode_cursor(payload)
        if sort == "scraps":
            payload["count"] = recipe.stats.scrap_count if recipe.stats else 0
            return _encode_cursor(payload)
        return _encode_cursor(payload)

    def get_recipe(self, recipe_id: int) -> Recipe:
        stmt = (
            select(Recipe)
            .options(
                joinedload(Recipe.stats),
                joinedload(Recipe.nutrition),
                joinedload(Recipe.classifications),
                selectinload(Recipe.ingredients_list),
                selectinload(Recipe.steps),
                selectinload(Recipe.labels),
                selectinload(Recipe.media),
                selectinload(Recipe.embeddings),
                joinedload(Recipe.source),
            )
            .where(Recipe.recipe_id == recipe_id)
        )
        recipe = self.db.execute(stmt).scalars().unique().one_or_none()
        if recipe is None:
            raise AdminRecipeNotFoundError(recipe_id)
        return recipe


def _parse_count_cursor(cursor: str, sort: str) -> tuple[int, int]:
    payload = _decode_cursor(cursor)
    if payload.get("sort") != sort:
        raise AdminRecipeInvalidCursorError("Cursor sort mismatch.")
    if "count" not in payload:
        raise AdminRecipeInvalidCursorError("Invalid cursor.")
    try:
        return int(payload["count"]), _cursor_recipe_id(payload)
    except (TypeError, ValueError) as exc:
        raise AdminRecipeInvalidCursorError("Invalid cursor.") from exc


def _cursor_recipe_id(payload: dict[str, Any]) -> int:
    try:
        return int(payload["recipe_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AdminRecipeInvalidCursorError("Invalid cursor.") from exc


def _encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(f"{cursor}{padding}".encode())
        payload = json.loads(raw)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AdminRecipeInvalidCursorError("Invalid cursor.") from exc
    if not isinstance(payload, dict) or "recipe_id" not in payload:
        raise AdminRecipeInvalidCursorError("Invalid cursor.")
    return payload
