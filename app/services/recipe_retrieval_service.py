from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.recipe import Recipe
from app.services.embedding_service import EmbeddingService, embedding_service


class RecipeRetrievalService:
    def __init__(
        self,
        embedder: EmbeddingService,
        session_factory: Callable[[], Session],
    ):
        self.embedder = embedder
        self.session_factory = session_factory

    def search_recipes(self, query: str, limit: int = 3) -> list[Recipe]:
        db = self.session_factory()
        try:
            query_vector = self.embedder.embed_query(query)
            stmt = (
                select(Recipe)
                .where(Recipe.is_active.is_(True), Recipe.embedding.is_not(None))
                .order_by(Recipe.embedding.cosine_distance(query_vector))
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
