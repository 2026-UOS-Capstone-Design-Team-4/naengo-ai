from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import INTERNAL_API_SECRET, TEMP_USER_ID
from app.db.session import get_db
from app.models.user import User


def get_current_user_id() -> int:
    return TEMP_USER_ID


def get_current_user(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> User:
    user = db.get(User, current_user_id)
    if not user or not user.is_active or user.is_blocked:
        raise ApiError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Authentication is required.",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise ApiError(
            status_code=403,
            code="FORBIDDEN",
            message="Admin permission is required.",
        )
    return current_user


def require_system(
    x_internal_secret: str | None = Header(default=None, alias="X-Internal-Secret"),
) -> None:
    if not INTERNAL_API_SECRET:
        raise ApiError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="Internal API secret is not configured.",
        )
    if x_internal_secret != INTERNAL_API_SECRET:
        raise ApiError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Internal authentication is required.",
        )
