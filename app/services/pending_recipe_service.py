import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.recipe import PendingRecipe
from app.models.user import User
from app.schemas.pending_recipe import (
    PendingRecipeAdminUpdate,
    PendingRecipeCreate,
    build_pending_recipe_payload,
)


class PendingRecipeInvalidCursorError(ValueError):
    pass


class PendingRecipeActiveDeleteError(ValueError):
    pass


class PendingRecipeService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_pending_recipes(self, user_id: int) -> list[PendingRecipe]:
        return (
            self.db.query(PendingRecipe)
            .filter(
                PendingRecipe.user_id == user_id,
                PendingRecipe.is_active.is_(True),
            )
            .order_by(PendingRecipe.created_at.desc())
            .all()
        )

    def get_admin_pending_recipes(
        self,
        *,
        status: str | None = None,
        is_active: bool | None = None,
        user_id: int | None = None,
        q: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[PendingRecipe], str | None]:
        cursor_id = (
            _parse_admin_pending_recipe_cursor(cursor)
            if cursor is not None
            else None
        )
        query = self.db.query(PendingRecipe)
        if status:
            query = query.filter(PendingRecipe.status == status)
        if is_active is not None:
            query = query.filter(PendingRecipe.is_active.is_(is_active))
        if user_id is not None:
            query = query.filter(PendingRecipe.user_id == user_id)
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                PendingRecipe.title.ilike(like_q)
                | PendingRecipe.submission_text.ilike(like_q)
            )
        if cursor_id is not None:
            query = query.filter(PendingRecipe.pending_recipe_id < cursor_id)

        rows = (
            query.order_by(PendingRecipe.pending_recipe_id.desc())
            .limit(limit + 1)
            .all()
        )
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            _build_admin_pending_recipe_cursor(items[-1].pending_recipe_id)
            if has_next and items
            else None
        )
        return items, next_cursor

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
                PendingRecipe.is_active.is_(True),
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
            submission_text=body.submission_text,
            draft_payload=build_pending_recipe_payload(body.draft_payload),
            ai_suggested_patch=build_pending_recipe_payload(),
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

        pending.is_active = False
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

        direct_fields = ["title", "submission_text"]
        for field in direct_fields:
            value = getattr(body, field)
            if value is not None:
                setattr(pending, field, value)

        nullable_fields = ["admin_note", "rejection_reason"]
        for field in nullable_fields:
            if field in body.model_fields_set:
                setattr(pending, field, getattr(body, field))

        if body.draft_payload is not None:
            pending.draft_payload = build_pending_recipe_payload(body.draft_payload)
        if body.ai_suggested_patch is not None:
            pending.ai_suggested_patch = build_pending_recipe_payload(
                body.ai_suggested_patch,
            )
        if body.validation_errors is not None:
            pending.validation_errors = body.validation_errors

        if body.status is not None and body.status != pending.status:
            pending.status = body.status
            pending.reviewed_at = datetime.now(UTC)
            if (
                body.status != "REJECTED"
                and "rejection_reason" not in body.model_fields_set
            ):
                pending.rejection_reason = None

        self.db.commit()
        self.db.refresh(pending)
        return pending

    def hard_delete_inactive_pending_recipe(self, pending_recipe_id: int) -> bool:
        pending = self.get_active_pending_recipe(pending_recipe_id)
        if not pending:
            return False
        if pending.is_active:
            raise PendingRecipeActiveDeleteError(
                "Active pending recipe cannot be hard-deleted.",
            )

        self.db.delete(pending)
        self.db.commit()
        return True


def _build_admin_pending_recipe_cursor(pending_recipe_id: int) -> str:
    payload: dict[str, Any] = {
        "sort": "latest",
        "pending_recipe_id": pending_recipe_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _parse_admin_pending_recipe_cursor(cursor: str) -> int:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(f"{cursor}{padding}".encode())
        payload = json.loads(raw)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PendingRecipeInvalidCursorError("Invalid cursor.") from exc
    if not isinstance(payload, dict) or payload.get("sort") != "latest":
        raise PendingRecipeInvalidCursorError("Invalid cursor.")
    try:
        return int(payload["pending_recipe_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PendingRecipeInvalidCursorError("Invalid cursor.") from exc
