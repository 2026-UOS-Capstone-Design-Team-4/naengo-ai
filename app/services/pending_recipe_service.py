import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import EMBEDDING_MODEL
from app.models.recipe import PendingRecipe, Recipe, RecipeEmbedding, RecipeMedia
from app.models.user import User
from app.schemas.pending_recipe import PendingRecipeAdminUpdate, PendingRecipeCreate
from app.services.embedding_service import embedding_service


class PendingRecipeApprovalError(ValueError):
    pass


class PendingRecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_pending_recipes(self, user_id: int) -> list[PendingRecipe]:
        return (
            self.db.query(PendingRecipe)
            .filter(PendingRecipe.user_id == user_id)
            .order_by(PendingRecipe.created_at.desc())
            .all()
        )

    def get_user_pending_recipe(
        self,
        pending_recipe_id: int,
        user_id: int,
    ) -> PendingRecipe | None:
        return (
            self.db.query(PendingRecipe)
            .filter(
                PendingRecipe.pending_recipe_id == pending_recipe_id,
                PendingRecipe.user_id == user_id,
            )
            .first()
        )

    def create_pending_recipe(
        self,
        body: PendingRecipeCreate,
        user_id: int,
    ) -> PendingRecipe | None:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        pending = PendingRecipe(
            user_id=user_id,
            title=body.title,
            content=body.content,
            description=body.description,
            ingredients=(
                [item.model_dump() for item in body.ingredients]
                if body.ingredients
                else None
            ),
            ingredients_raw=body.ingredients_raw,
            instructions=body.instructions,
            servings=body.servings,
            cooking_time=body.cooking_time,
            calories=body.calories,
            difficulty=body.difficulty,
            category=body.category,
            tags=body.tags,
            tips=body.tips,
            video_url=body.video_url,
            image_url=body.image_url,
        )
        self.db.add(pending)
        self.db.commit()
        self.db.refresh(pending)
        return pending

    def delete_user_pending_recipe(
        self,
        pending_recipe_id: int,
        user_id: int,
    ) -> bool:
        pending = self.get_user_pending_recipe(pending_recipe_id, user_id)
        if not pending:
            return False

        pending.status = "REJECTED"
        self.db.commit()
        return True

    def get_active_pending_recipe(
        self,
        pending_recipe_id: int,
    ) -> PendingRecipe | None:
        return (
            self.db.query(PendingRecipe)
            .filter(
                PendingRecipe.pending_recipe_id == pending_recipe_id,
            )
            .first()
        )

    def update_pending_recipe_status(
        self,
        pending_recipe_id: int,
        body: PendingRecipeAdminUpdate,
    ) -> PendingRecipe | None:
        pending = self.get_active_pending_recipe(pending_recipe_id)
        if not pending:
            return None

        recipe_fields = [
            "title",
            "content",
            "description",
            "ingredients_raw",
            "instructions",
            "servings",
            "cooking_time",
            "calories",
            "difficulty",
            "category",
            "tags",
            "tips",
            "video_url",
            "image_url",
            "admin_note",
        ]
        for field in recipe_fields:
            value = getattr(body, field)
            if value is not None:
                setattr(pending, field, value)

        if body.ingredients is not None:
            pending.ingredients = [item.model_dump() for item in body.ingredients]

        if body.status is not None and body.status != pending.status:
            previous_status = pending.status
            pending.status = body.status
            pending.reviewed_at = datetime.now(UTC)
            if body.status == "APPROVED" and previous_status != "APPROVED":
                self._promote_to_recipe(pending)

        self.db.commit()
        self.db.refresh(pending)
        return pending

    def _promote_to_recipe(self, pending: PendingRecipe):
        missing_fields = self._get_missing_recipe_fields(pending)
        if missing_fields:
            missing = ", ".join(missing_fields)
            message = f"Cannot approve recipe with missing fields: {missing}"
            raise PendingRecipeApprovalError(message)

        existing_recipe = self._find_existing_promoted_recipe(pending)
        if existing_recipe:
            return

        recipe_payload = self._pending_to_recipe_payload(pending)
        embedding_text = self._build_embedding_text(recipe_payload)
        recipe = Recipe(**recipe_payload)
        self.db.add(recipe)
        self.db.flush()
        self.db.add(
            RecipeEmbedding(
                recipe_id=recipe.recipe_id,
                embedding_type="RECIPE_SEARCH",
                model=EMBEDDING_MODEL,
                content_hash=hashlib.sha256(embedding_text.encode()).hexdigest(),
                embedding=embedding_service.embed_query(embedding_text),
            )
        )

    def _get_missing_recipe_fields(self, pending: PendingRecipe) -> list[str]:
        required_fields = [
            "title",
            "description",
            "ingredients",
            "ingredients_raw",
            "instructions",
            "servings",
            "cooking_time",
            "difficulty",
            "category",
        ]
        return [field for field in required_fields if not getattr(pending, field)]

    def _find_existing_promoted_recipe(self, pending: PendingRecipe) -> Recipe | None:
        if pending.video_url:
            return (
                self.db.query(Recipe)
                .join(RecipeMedia, Recipe.recipe_id == RecipeMedia.recipe_id)
                .filter(
                    RecipeMedia.storage_url == pending.video_url,
                    Recipe.author_type == "USER",
                    Recipe.author_id == pending.user_id,
                )
                .first()
            )
        return (
            self.db.query(Recipe)
            .filter(
                Recipe.title == pending.title,
                Recipe.author_type == "USER",
                Recipe.author_id == pending.user_id,
                Recipe.summary == pending.content,
            )
            .first()
        )

    def _pending_to_recipe_payload(self, pending: PendingRecipe) -> dict:
        return {
            "title": pending.title,
            "description": pending.description,
            "ingredients": pending.ingredients,
            "instructions": pending.instructions,
            "servings": pending.servings,
            "total_time_minutes": pending.cooking_time,
            "calories": pending.calories,
            "difficulty": pending.difficulty,
            "category": pending.category or [],
            "tags": pending.tags or [],
            "tips": pending.tips or [],
            "summary": pending.content,
            "video_url": pending.video_url,
            "image_url": pending.image_url,
            "author_type": "USER",
            "author_id": pending.user_id,
        }

    def _build_embedding_text(self, recipe: dict) -> str:
        parts = [
            recipe["title"],
            recipe["description"],
            " ".join(item.get("name", "") for item in recipe.get("ingredients") or []),
            " ".join(recipe["category"] or []),
            " ".join(recipe["tags"] or []),
            " ".join(recipe["tips"] or []),
        ]
        if recipe["total_time_minutes"]:
            parts.append(f"{recipe['total_time_minutes']} minutes")
        if recipe["difficulty"]:
            parts.append(recipe["difficulty"])
        return " ".join(str(part) for part in parts if part)
