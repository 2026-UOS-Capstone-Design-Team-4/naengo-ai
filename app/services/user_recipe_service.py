import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.recipe import UserRecipe
from app.models.user import User
from app.schemas.user_recipe import (
    UserRecipeAdminUpdate,
    UserRecipeCreate,
    build_user_recipe_payload,
)


class UserRecipeInvalidCursorError(ValueError):
    pass


class UserRecipeActiveDeleteError(ValueError):
    pass


class UserRecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_recipes(self, user_id: int) -> list[UserRecipe]:
        return (
            self.db.query(UserRecipe)
            .filter(
                UserRecipe.user_id == user_id,
                UserRecipe.is_active.is_(True),
            )
            .order_by(UserRecipe.created_at.desc())
            .all()
        )

    def get_admin_user_recipes(
        self,
        *,
        status: str | None = None,
        is_active: bool | None = None,
        user_id: int | None = None,
        q: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[UserRecipe], str | None]:
        cursor_id = (
            _parse_admin_user_recipe_cursor(cursor)
            if cursor is not None
            else None
        )
        query = self.db.query(UserRecipe)
        if status:
            query = query.filter(UserRecipe.status == status)
        if is_active is not None:
            query = query.filter(UserRecipe.is_active.is_(is_active))
        if user_id is not None:
            query = query.filter(UserRecipe.user_id == user_id)
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                UserRecipe.title.ilike(like_q)
                | UserRecipe.submission_text.ilike(like_q)
            )
        if cursor_id is not None:
            query = query.filter(UserRecipe.user_recipe_id < cursor_id)

        rows = (
            query.order_by(UserRecipe.user_recipe_id.desc())
            .limit(limit + 1)
            .all()
        )
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            _build_admin_user_recipe_cursor(items[-1].user_recipe_id)
            if has_next and items
            else None
        )
        return items, next_cursor

    def get_user_recipe(
        self,
        user_recipe_id: int,
        user_id: int,
    ) -> UserRecipe | None:
        return (
            self.db.query(UserRecipe)
            .filter(
                UserRecipe.user_recipe_id == user_recipe_id,
                UserRecipe.user_id == user_id,
                UserRecipe.is_active.is_(True),
            )
            .first()
        )

    def create_user_recipe(
        self,
        body: UserRecipeCreate,
        user_id: int,
    ) -> UserRecipe | None:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        recipe = UserRecipe(
            user_id=user_id,
            title=body.title,
            submission_text=body.submission_text,
            draft_payload=build_user_recipe_payload(),
            ai_suggested_patch=build_user_recipe_payload(),
        )
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def delete_user_recipe(
        self,
        user_recipe_id: int,
        user_id: int,
    ) -> bool:
        recipe = self.get_user_recipe(user_recipe_id, user_id)
        if not recipe:
            return False

        recipe.is_active = False
        self.db.commit()
        return True

    def get_active_user_recipe(
        self,
        user_recipe_id: int,
    ) -> UserRecipe | None:
        return (
            self.db.query(UserRecipe)
            .filter(
                UserRecipe.user_recipe_id == user_recipe_id,
            )
            .first()
        )

    def update_user_recipe_status(
        self,
        user_recipe_id: int,
        body: UserRecipeAdminUpdate,
    ) -> UserRecipe | None:
        recipe = self.get_active_user_recipe(user_recipe_id)
        if not recipe:
            return None

        direct_fields = ["title", "submission_text"]
        for field in direct_fields:
            value = getattr(body, field)
            if value is not None:
                setattr(recipe, field, value)

        nullable_fields = ["admin_note", "rejection_reason"]
        for field in nullable_fields:
            if field in body.model_fields_set:
                setattr(recipe, field, getattr(body, field))

        if body.draft_payload is not None:
            recipe.draft_payload = build_user_recipe_payload(body.draft_payload)
        if body.ai_suggested_patch is not None:
            recipe.ai_suggested_patch = build_user_recipe_payload(
                body.ai_suggested_patch,
            )
        if body.validation_errors is not None:
            recipe.validation_errors = body.validation_errors

        if body.status is not None and body.status != recipe.status:
            recipe.status = body.status
            recipe.reviewed_at = datetime.now(UTC)
            if (
                body.status != "REJECTED"
                and "rejection_reason" not in body.model_fields_set
            ):
                recipe.rejection_reason = None

        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def hard_delete_inactive_user_recipe(self, user_recipe_id: int) -> bool:
        recipe = self.get_active_user_recipe(user_recipe_id)
        if not recipe:
            return False
        if recipe.is_active:
            raise UserRecipeActiveDeleteError(
                "Active user recipe cannot be hard-deleted.",
            )

        self.db.delete(recipe)
        self.db.commit()
        return True


def _build_admin_user_recipe_cursor(user_recipe_id: int) -> str:
    payload: dict[str, Any] = {
        "sort": "latest",
        "user_recipe_id": user_recipe_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _build_user_recipe_title(submission_text: str) -> str:
    for line in submission_text.splitlines():
        title = line.strip()
        if title:
            return title[:255]
    return "사용자 제출 레시피"


def _parse_admin_user_recipe_cursor(cursor: str) -> int:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(f"{cursor}{padding}".encode())
        payload = json.loads(raw)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UserRecipeInvalidCursorError("Invalid cursor.") from exc
    if not isinstance(payload, dict) or payload.get("sort") != "latest":
        raise UserRecipeInvalidCursorError("Invalid cursor.")
    try:
        return int(payload["user_recipe_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UserRecipeInvalidCursorError("Invalid cursor.") from exc
