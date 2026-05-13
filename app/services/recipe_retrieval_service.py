from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe, RecipeEmbedding
from app.models.recipe_source import RecipeSource  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401
from app.services.embedding_service import EmbeddingService, embedding_service


class RecipeRetrievalService:
    def __init__(
        self,
        embedder: EmbeddingService,
        session_factory: Callable[[], Session],
    ):
        self.embedder = embedder
        self.session_factory = session_factory

    def search_recipes(
        self, query: str, limit: int = 3, score_cutoff: float = 0.65
    ) -> list[Recipe]:
        db = self.session_factory()
        try:
            query_vector = self.embedder.embed_query(query)
            dist_expr = RecipeEmbedding.embedding.cosine_distance(query_vector)
            stmt = (
                select(Recipe)
                .join(RecipeEmbedding, Recipe.recipe_id == RecipeEmbedding.recipe_id)
                .where(
                    Recipe.is_active.is_(True),
                    RecipeEmbedding.embedding_type == "RECIPE_SEARCH",
                    dist_expr < score_cutoff,
                )
                .options(
                    selectinload(Recipe.ingredients_list),
                    selectinload(Recipe.steps),
                    selectinload(Recipe.labels),
                    selectinload(Recipe.media),
                )
                .order_by(dist_expr)
                .limit(limit)
            )
            return db.execute(stmt).scalars().all()
        finally:
            db.close()

    def recipe_to_payload(self, recipe: Recipe) -> dict:
        return {
            "id": recipe.recipe_id,
            "title": recipe.title,
            "description": recipe.description,
            "ingredients": recipe.ingredients,
            "ingredients_raw": recipe.ingredients_raw,
            "instructions": recipe.instructions,
            "servings": float(recipe.servings) if recipe.servings else None,
            "cooking_time": recipe.cooking_time,
            "calories": recipe.calories,
            "difficulty": recipe.difficulty,
            "category": recipe.category,
            "tags": recipe.tags,
            "tips": recipe.tips,
            "video_url": recipe.video_url,
            "image_url": recipe.image_url,
            "author_type": recipe.author_type,
        }


recipe_retrieval_service = RecipeRetrievalService(
    embedder=embedding_service,
    session_factory=SessionLocal,
)
