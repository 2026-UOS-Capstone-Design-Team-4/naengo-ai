import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.recipe import UserRecipe, UserRecipeReport
from app.schemas.user_recipe_report import (
    UserRecipeReportAdminUpdate,
    UserRecipeReportCreate,
)


class UserRecipeReportNotFoundError(ValueError):
    pass


class UserRecipeReportAlreadyExistsError(ValueError):
    pass


class UserRecipeReportOwnRecipeError(ValueError):
    pass


class UserRecipeReportInvalidCursorError(ValueError):
    pass


class UserRecipeReportService:
    def __init__(self, db: Session):
        self.db = db

    def create_report(
        self,
        user_recipe_id: int,
        reporter_user_id: int,
        body: UserRecipeReportCreate,
    ) -> UserRecipeReport:
        recipe = (
            self.db.query(UserRecipe)
            .filter(
                UserRecipe.user_recipe_id == user_recipe_id,
                UserRecipe.status == "APPROVED",
                UserRecipe.is_active.is_(True),
            )
            .first()
        )
        if not recipe:
            raise UserRecipeReportNotFoundError("User recipe not found.")
        if recipe.user_id == reporter_user_id:
            raise UserRecipeReportOwnRecipeError("Cannot report own recipe.")

        existing = (
            self.db.query(UserRecipeReport)
            .filter(
                UserRecipeReport.user_recipe_id == user_recipe_id,
                UserRecipeReport.reporter_user_id == reporter_user_id,
            )
            .first()
        )
        if existing:
            raise UserRecipeReportAlreadyExistsError("Already reported.")

        report = UserRecipeReport(
            user_recipe_id=user_recipe_id,
            reporter_user_id=reporter_user_id,
            recipe_owner_user_id=recipe.user_id,
            reason=body.reason,
            description=body.description,
            status="PENDING",
        )
        self.db.add(report)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise UserRecipeReportAlreadyExistsError("Already reported.") from exc
        self.db.refresh(report)
        return report

    def get_admin_reports(
        self,
        *,
        status: str | None = None,
        user_recipe_id: int | None = None,
        reporter_user_id: int | None = None,
        recipe_owner_user_id: int | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[UserRecipeReport], str | None]:
        cursor_id = _parse_report_cursor(cursor) if cursor is not None else None
        query = self.db.query(UserRecipeReport).options(
            selectinload(UserRecipeReport.user_recipe),
            selectinload(UserRecipeReport.reporter),
            selectinload(UserRecipeReport.recipe_owner),
            selectinload(UserRecipeReport.reviewer),
        )
        if status:
            query = query.filter(UserRecipeReport.status == status)
        if user_recipe_id is not None:
            query = query.filter(UserRecipeReport.user_recipe_id == user_recipe_id)
        if reporter_user_id is not None:
            query = query.filter(
                UserRecipeReport.reporter_user_id == reporter_user_id
            )
        if recipe_owner_user_id is not None:
            query = query.filter(
                UserRecipeReport.recipe_owner_user_id == recipe_owner_user_id
            )
        if cursor_id is not None:
            query = query.filter(UserRecipeReport.report_id < cursor_id)

        rows = query.order_by(UserRecipeReport.report_id.desc()).limit(limit + 1).all()
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = (
            _build_report_cursor(items[-1].report_id) if has_next and items else None
        )
        return items, next_cursor

    def get_admin_report(self, report_id: int) -> UserRecipeReport | None:
        return (
            self.db.query(UserRecipeReport)
            .options(
                selectinload(UserRecipeReport.user_recipe),
                selectinload(UserRecipeReport.reporter),
                selectinload(UserRecipeReport.recipe_owner),
                selectinload(UserRecipeReport.reviewer),
            )
            .filter(UserRecipeReport.report_id == report_id)
            .first()
        )

    def update_admin_report(
        self,
        report_id: int,
        body: UserRecipeReportAdminUpdate,
        reviewer_user_id: int,
    ) -> UserRecipeReport | None:
        report = self.get_admin_report(report_id)
        if not report:
            return None

        if body.status is not None and body.status != report.status:
            report.status = body.status
            report.reviewed_by = reviewer_user_id
            report.reviewed_at = datetime.now(UTC)
        if "review_note" in body.model_fields_set:
            report.review_note = body.review_note

        self.db.commit()
        self.db.refresh(report)
        return report


def _build_report_cursor(report_id: int) -> str:
    payload: dict[str, Any] = {
        "sort": "latest",
        "report_id": report_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _parse_report_cursor(cursor: str) -> int:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(f"{cursor}{padding}".encode())
        payload = json.loads(raw)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UserRecipeReportInvalidCursorError("Invalid cursor.") from exc
    if not isinstance(payload, dict) or payload.get("sort") != "latest":
        raise UserRecipeReportInvalidCursorError("Invalid cursor.")
    try:
        return int(payload["report_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UserRecipeReportInvalidCursorError("Invalid cursor.") from exc
