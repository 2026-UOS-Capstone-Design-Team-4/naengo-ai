from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.recipe import Recipe, RecipeStats
from app.models.social import Like, Scrap
from app.schemas.recipe import (
    RecipeListItemResponse,
    RecipeListResponse,
    RecipeStatsResponse,
)


class RecipeNotFoundError(Exception):
    pass


class AlreadyLikedError(Exception):
    pass


class NotLikedError(Exception):
    pass


class AlreadyScrappedError(Exception):
    pass


class NotScrappedError(Exception):
    pass


class RecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_recipe(self, recipe_id: int, user_id: int) -> RecipeListItemResponse:
        stmt = (
            select(Recipe)
            .options(joinedload(Recipe.stats))
            .where(Recipe.recipe_id == recipe_id, Recipe.is_active.is_(True))
        )
        recipe = self.db.execute(stmt).scalars().unique().one_or_none()
        if recipe is None:
            raise RecipeNotFoundError(recipe_id)
        liked_ids, scrapped_ids = self._get_social_sets(user_id, [recipe_id])
        return self._to_list_item(recipe, liked_ids, scrapped_ids)

    def get_recipes_by_latest(
        self, user_id: int, cursor: str | None, limit: int
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

        recipe_ids = [r.recipe_id for r in items]
        liked_ids, scrapped_ids = self._get_social_sets(user_id, recipe_ids)

        return RecipeListResponse(
            items=[self._to_list_item(r, liked_ids, scrapped_ids) for r in items],
            next_cursor=str(items[-1].recipe_id) if has_next else None,
            has_next=has_next,
        )

    def get_recipes_by_likes(
        self, user_id: int, cursor: str | None, limit: int
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

        recipe_ids = [r.recipe_id for r in items]
        liked_ids, scrapped_ids = self._get_social_sets(user_id, recipe_ids)

        return RecipeListResponse(
            items=[self._to_list_item(r, liked_ids, scrapped_ids) for r in items],
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

        recipe_ids = [s.recipe_id for s in items]
        liked_ids, _ = self._get_social_sets(user_id, recipe_ids)
        # 스크랩 목록의 모든 레시피는 is_scrapped = True
        scrapped_ids = set(recipe_ids)

        return RecipeListResponse(
            items=[
                self._to_list_item(s.recipe, liked_ids, scrapped_ids) for s in items
            ],
            next_cursor=str(items[-1].scrap_id) if has_next else None,
            has_next=has_next,
        )

    def like(self, recipe_id: int, user_id: int) -> RecipeStatsResponse:
        self._get_active_recipe(recipe_id)
        existing = self.db.execute(
            select(Like).where(Like.user_id == user_id, Like.recipe_id == recipe_id)
        ).scalar_one_or_none()
        if existing:
            raise AlreadyLikedError()
        self.db.add(Like(user_id=user_id, recipe_id=recipe_id))
        self.db.commit()
        return self._fetch_stats(recipe_id)

    def unlike(self, recipe_id: int, user_id: int) -> RecipeStatsResponse:
        self._get_active_recipe(recipe_id)
        existing = self.db.execute(
            select(Like).where(Like.user_id == user_id, Like.recipe_id == recipe_id)
        ).scalar_one_or_none()
        if not existing:
            raise NotLikedError()
        self.db.delete(existing)
        self.db.commit()
        return self._fetch_stats(recipe_id)

    def scrap(self, recipe_id: int, user_id: int) -> RecipeStatsResponse:
        self._get_active_recipe(recipe_id)
        existing = self.db.execute(
            select(Scrap).where(Scrap.user_id == user_id, Scrap.recipe_id == recipe_id)
        ).scalar_one_or_none()
        if existing:
            raise AlreadyScrappedError()
        self.db.add(Scrap(user_id=user_id, recipe_id=recipe_id))
        self.db.commit()
        return self._fetch_stats(recipe_id)

    def unscrap(self, recipe_id: int, user_id: int) -> RecipeStatsResponse:
        self._get_active_recipe(recipe_id)
        existing = self.db.execute(
            select(Scrap).where(Scrap.user_id == user_id, Scrap.recipe_id == recipe_id)
        ).scalar_one_or_none()
        if not existing:
            raise NotScrappedError()
        self.db.delete(existing)
        self.db.commit()
        return self._fetch_stats(recipe_id)

    def _get_active_recipe(self, recipe_id: int) -> Recipe:
        recipe = self.db.execute(
            select(Recipe).where(
                Recipe.recipe_id == recipe_id, Recipe.is_active.is_(True)
            )
        ).scalar_one_or_none()
        if recipe is None:
            raise RecipeNotFoundError(recipe_id)
        return recipe

    def _fetch_stats(self, recipe_id: int) -> RecipeStatsResponse:
        stats = self.db.get(RecipeStats, recipe_id)
        return RecipeStatsResponse(
            likes_count=stats.likes_count if stats else 0,
            scrap_count=stats.scrap_count if stats else 0,
        )

    def _get_social_sets(
        self, user_id: int, recipe_ids: list[int]
    ) -> tuple[set[int], set[int]]:
        if not recipe_ids:
            return set(), set()
        liked = set(
            self.db.execute(
                select(Like.recipe_id).where(
                    Like.user_id == user_id, Like.recipe_id.in_(recipe_ids)
                )
            ).scalars()
        )
        scrapped = set(
            self.db.execute(
                select(Scrap.recipe_id).where(
                    Scrap.user_id == user_id, Scrap.recipe_id.in_(recipe_ids)
                )
            ).scalars()
        )
        return liked, scrapped

    def _to_list_item(
        self,
        recipe: Recipe,
        liked_ids: set[int] | None = None,
        scrapped_ids: set[int] | None = None,
    ) -> RecipeListItemResponse:
        item = RecipeListItemResponse.model_validate(recipe)
        item.likes_count = recipe.stats.likes_count if recipe.stats else 0
        item.scrap_count = recipe.stats.scrap_count if recipe.stats else 0
        item.is_liked = recipe.recipe_id in (liked_ids or set())
        item.is_scrapped = recipe.recipe_id in (scrapped_ids or set())
        return item
