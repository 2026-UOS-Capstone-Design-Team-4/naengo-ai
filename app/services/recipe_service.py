from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.recipe import Recipe, RecipeStats
from app.models.social import Scrap
from app.schemas.recipe import RecipeListItemResponse, RecipeListResponse


class RecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_recipes_by_latest(
        self, cursor: str | None, limit: int
    ) -> RecipeListResponse:
        cursor_id = int(cursor) if cursor else None

        stmt = (
            select(Recipe)
            .options(joinedload(Recipe.stats))
            .where(Recipe.is_active.is_(True))
        )
        if cursor_id is not None:
            stmt = stmt.where(Recipe.recipe_id < cursor_id)
        stmt = stmt.order_by(Recipe.recipe_id.desc()).limit(limit + 1)

        recipes = list(self.db.execute(stmt).scalars().unique().all())
        has_next = len(recipes) > limit
        items = recipes[:limit]

        return RecipeListResponse(
            items=[self._to_list_item(r) for r in items],
            next_cursor=str(items[-1].recipe_id) if has_next else None,
            has_next=has_next,
        )

    def get_recipes_by_likes(
        self, cursor: str | None, limit: int
    ) -> RecipeListResponse:
        cursor_likes, cursor_id = None, None
        if cursor:
            parts = cursor.split("_", 1)
            cursor_likes, cursor_id = int(parts[0]), int(parts[1])

        coalesced_likes = func.coalesce(RecipeStats.likes_count, 0)

        stmt = (
            select(Recipe)
            .outerjoin(RecipeStats, Recipe.recipe_id == RecipeStats.recipe_id)
            .options(joinedload(Recipe.stats))
            .where(Recipe.is_active.is_(True))
        )
        if cursor_likes is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    coalesced_likes < cursor_likes,
                    and_(coalesced_likes == cursor_likes, Recipe.recipe_id < cursor_id),
                )
            )
        stmt = stmt.order_by(coalesced_likes.desc(), Recipe.recipe_id.desc()).limit(
            limit + 1
        )

        recipes = list(self.db.execute(stmt).scalars().unique().all())
        has_next = len(recipes) > limit
        items = recipes[:limit]

        next_cursor = None
        if has_next and items:
            last = items[-1]
            lc = last.stats.likes_count if last.stats else 0
            next_cursor = f"{lc}_{last.recipe_id}"

        return RecipeListResponse(
            items=[self._to_list_item(r) for r in items],
            next_cursor=next_cursor,
            has_next=has_next,
        )

    def get_scraps(
        self, user_id: int, cursor: str | None, limit: int
    ) -> RecipeListResponse:
        cursor_id = int(cursor) if cursor else None

        stmt = (
            select(Scrap)
            .join(Recipe, Scrap.recipe_id == Recipe.recipe_id)
            .options(joinedload(Scrap.recipe).joinedload(Recipe.stats))
            .where(Scrap.user_id == user_id, Recipe.is_active.is_(True))
        )
        if cursor_id is not None:
            stmt = stmt.where(Scrap.scrap_id < cursor_id)
        stmt = stmt.order_by(Scrap.scrap_id.desc()).limit(limit + 1)

        scraps = list(self.db.execute(stmt).scalars().unique().all())
        has_next = len(scraps) > limit
        items = scraps[:limit]

        return RecipeListResponse(
            items=[self._to_list_item(s.recipe) for s in items],
            next_cursor=str(items[-1].scrap_id) if has_next else None,
            has_next=has_next,
        )

    def _to_list_item(self, recipe: Recipe) -> RecipeListItemResponse:
        item = RecipeListItemResponse.model_validate(recipe)
        item.likes_count = recipe.stats.likes_count if recipe.stats else 0
        item.scrap_count = recipe.stats.scrap_count if recipe.stats else 0
        return item
