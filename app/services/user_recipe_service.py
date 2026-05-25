import base64
import binascii
import json
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models.recipe import (
    UserRecipe,
    UserRecipeIngredient,
    UserRecipeLabel,
    UserRecipeNutrition,
    UserRecipeStep,
)
from app.models.user import User
from app.schemas.user_recipe import (
    UserRecipeAdminUpdate,
    UserRecipeCreate,
)
from app.services.storage_service import ChatImageStorage, user_recipe_image_storage

ALLOWED_USER_RECIPE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_USER_RECIPE_IMAGE_BYTES = 10 * 1024 * 1024


class UserRecipeInvalidCursorError(ValueError):
    pass


class UserRecipeActiveDeleteError(ValueError):
    pass


class UserRecipeImageValidationError(ValueError):
    pass


class UserRecipeStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class UserRecipeImageUpload:
    filename: str
    content_type: str
    data: bytes


class UserRecipeService:
    def __init__(
        self,
        db: Session,
        image_storage: ChatImageStorage = user_recipe_image_storage,
    ):
        self.db = db
        self.image_storage = image_storage

    def get_user_recipes(self, user_id: int) -> list[UserRecipe]:
        return (
            self.db.query(UserRecipe)
            .options(
                selectinload(UserRecipe.labels),
            )
            .filter(
                UserRecipe.user_id == user_id,
                UserRecipe.is_active.is_(True),
            )
            .order_by(UserRecipe.created_at.desc())
            .all()
        )

    def get_approved_user_recipes(self) -> list[UserRecipe]:
        return (
            self.db.query(UserRecipe)
            .options(
                selectinload(UserRecipe.labels),
            )
            .filter(
                UserRecipe.status == "APPROVED",
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
            _parse_admin_user_recipe_cursor(cursor) if cursor is not None else None
        )
        query = self.db.query(UserRecipe).options(
            selectinload(UserRecipe.ingredients),
            selectinload(UserRecipe.steps),
            selectinload(UserRecipe.labels),
            selectinload(UserRecipe.nutrition),
        )
        if status:
            query = query.filter(UserRecipe.status == status)
        if is_active is not None:
            query = query.filter(UserRecipe.is_active.is_(is_active))
        if user_id is not None:
            query = query.filter(UserRecipe.user_id == user_id)
        if q:
            like_q = f"%{q}%"
            query = query.filter(UserRecipe.title.ilike(like_q))
        if cursor_id is not None:
            query = query.filter(UserRecipe.user_recipe_id < cursor_id)

        rows = query.order_by(UserRecipe.user_recipe_id.desc()).limit(limit + 1).all()
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
            .options(
                selectinload(UserRecipe.ingredients),
                selectinload(UserRecipe.steps),
                selectinload(UserRecipe.labels),
                selectinload(UserRecipe.nutrition),
            )
            .filter(
                UserRecipe.user_recipe_id == user_recipe_id,
                UserRecipe.user_id == user_id,
                UserRecipe.is_active.is_(True),
            )
            .first()
        )

    def get_approved_user_recipe(
        self,
        user_recipe_id: int,
    ) -> UserRecipe | None:
        return (
            self.db.query(UserRecipe)
            .options(
                selectinload(UserRecipe.ingredients),
                selectinload(UserRecipe.steps),
                selectinload(UserRecipe.labels),
                selectinload(UserRecipe.nutrition),
            )
            .filter(
                UserRecipe.user_recipe_id == user_recipe_id,
                UserRecipe.status == "APPROVED",
                UserRecipe.is_active.is_(True),
            )
            .first()
        )

    def create_user_recipe(
        self,
        body: UserRecipeCreate,
        user_id: int,
        *,
        main_image: UserRecipeImageUpload | None = None,
        step_images: list[UserRecipeImageUpload] | None = None,
    ) -> UserRecipe | None:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        step_image_map = _build_step_image_map(step_images or [])
        expected_step_image_keys = {
            step.client_image_key for step in body.steps if step.client_image_key
        }
        extra_image_keys = set(step_image_map) - expected_step_image_keys
        missing_image_keys = expected_step_image_keys - set(step_image_map)
        if extra_image_keys:
            raise UserRecipeImageValidationError(
                f"Unmatched step images: {', '.join(sorted(extra_image_keys))}",
            )
        if missing_image_keys:
            raise UserRecipeImageValidationError(
                f"Missing step images: {', '.join(sorted(missing_image_keys))}",
            )

        recipe = UserRecipe(
            user_id=user_id,
            title=body.title,
            description=body.description,
            servings=body.servings,
            cooking_time_minutes=body.cooking_time_minutes,
            kcal_per_serving=body.kcal_per_serving,
            difficulty=body.difficulty,
            source_url=body.source_url,
        )
        self.db.add(recipe)
        self.db.flush()

        if main_image is not None:
            recipe.main_image_url = self._upload_image(
                main_image,
                _image_key(
                    user_id,
                    recipe.user_recipe_id,
                    "main",
                    main_image.filename,
                ),
            )

        recipe.ingredients = [
            UserRecipeIngredient(**item.model_dump(exclude_unset=True), sort_order=i)
            for i, item in enumerate(body.ingredients)
        ]
        recipe.steps = [
            UserRecipeStep(
                step_no=step.step_no,
                instruction=step.instruction,
                image_url=(
                    self._upload_image(
                        step_image_map[step.client_image_key],
                        _image_key(
                            user_id,
                            recipe.user_recipe_id,
                            f"steps/{step.step_no}",
                            step_image_map[step.client_image_key].filename,
                        ),
                    )
                    if step.client_image_key
                    else None
                ),
                tip=step.tip,
                sort_order=i,
            )
            for i, step in enumerate(body.steps)
        ]
        recipe.labels = _build_labels(
            body.category, body.tags, body.tips, body.warnings
        )
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def _upload_image(self, image: UserRecipeImageUpload, key: str) -> str:
        _validate_image(image)
        try:
            url = self.image_storage.upload_bytes(image.data, key, image.content_type)
        except Exception as exc:
            raise UserRecipeStorageError("Image storage is unavailable.") from exc
        if url is None:
            raise UserRecipeStorageError("Image storage is not configured.")
        return url

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

        direct_fields = ["title"]
        for field in direct_fields:
            value = getattr(body, field)
            if value is not None:
                setattr(recipe, field, value)

        nullable_fields = [
            "description",
            "servings",
            "yield_quantity",
            "yield_unit",
            "cooking_time_minutes",
            "kcal_per_serving",
            "difficulty",
            "source_url",
            "main_image_url",
            "rejection_reason",
        ]
        for field in nullable_fields:
            if field in body.model_fields_set:
                setattr(recipe, field, getattr(body, field))

        if body.ingredients is not None:
            recipe.ingredients = [
                UserRecipeIngredient(**item.model_dump(exclude_unset=True))
                for item in body.ingredients
            ]
        if body.steps is not None:
            recipe.steps = [
                UserRecipeStep(**item.model_dump(exclude_unset=True))
                for item in body.steps
            ]
        if body.labels is not None:
            recipe.labels = [
                UserRecipeLabel(**item.model_dump(exclude_unset=True))
                for item in body.labels
            ]
        if "nutrition" in body.model_fields_set:
            recipe.nutrition = (
                UserRecipeNutrition(**body.nutrition.model_dump(exclude_unset=True))
                if body.nutrition is not None
                else None
            )
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


def _validate_image(image: UserRecipeImageUpload) -> None:
    if image.content_type not in ALLOWED_USER_RECIPE_IMAGE_TYPES:
        raise UserRecipeImageValidationError("Unsupported image content type.")
    if len(image.data) > MAX_USER_RECIPE_IMAGE_BYTES:
        raise UserRecipeImageValidationError("Image file is too large.")
    if not image.data:
        raise UserRecipeImageValidationError("Image file is empty.")


def _build_step_image_map(
    images: list[UserRecipeImageUpload],
) -> dict[str, UserRecipeImageUpload]:
    result: dict[str, UserRecipeImageUpload] = {}
    for image in images:
        key = _client_image_key_from_filename(image.filename)
        if key in result:
            raise UserRecipeImageValidationError(f"Duplicate step image key: {key}")
        result[key] = image
    return result


def _client_image_key_from_filename(filename: str) -> str:
    stem = filename.rsplit("/", maxsplit=1)[-1].rsplit("\\", maxsplit=1)[-1]
    return stem.rsplit(".", maxsplit=1)[0]


def _image_key(user_id: int, user_recipe_id: int, scope: str, filename: str) -> str:
    extension = _image_extension(filename)
    return (
        f"user-recipes/{user_id}/{user_recipe_id}/{scope}/{uuid.uuid4().hex}{extension}"
    )


def _image_extension(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    guess = mimetypes.guess_extension(content_type or "")
    if guess in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if guess == ".jpeg" else guess
    suffix = filename.rsplit(".", maxsplit=1)
    if len(suffix) == 2 and suffix[1].lower() in {"jpg", "jpeg", "png", "webp"}:
        return f".{suffix[1].lower()}".replace(".jpeg", ".jpg")
    return ".bin"


def _build_labels(
    category: list[str],
    tags: list[str],
    tips: list[str],
    warnings: list[str],
) -> list[UserRecipeLabel]:
    labels = []
    for i, v in enumerate(category):
        labels.append(
            UserRecipeLabel(
                label_type="CATEGORY", label_value=v, source="ADMIN", sort_order=i
            )
        )
    for i, v in enumerate(tags):
        labels.append(
            UserRecipeLabel(
                label_type="TAG", label_value=v, source="ADMIN", sort_order=i
            )
        )
    for i, v in enumerate(tips):
        labels.append(
            UserRecipeLabel(
                label_type="TIP", label_value=v, source="ADMIN", sort_order=i
            )
        )
    for i, v in enumerate(warnings):
        labels.append(
            UserRecipeLabel(
                label_type="WARNING", label_value=v, source="ADMIN", sort_order=i
            )
        )
    return labels


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
