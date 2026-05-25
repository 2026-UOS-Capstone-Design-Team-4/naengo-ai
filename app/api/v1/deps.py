from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import INTERNAL_API_SECRET, JWT_ALGORITHM, JWT_SECRET_KEY
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import (
    AccessTokenPayload,
    AuthService,
    TokenValidationError,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccessTokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Bearer access token is required.",
        )
    if not JWT_SECRET_KEY:
        raise ApiError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="JWT secret key is not configured.",
        )
    try:
        return AuthService(JWT_SECRET_KEY, JWT_ALGORITHM).decode_access_token(
            credentials.credentials
        )
    except TokenValidationError as exc:
        raise ApiError(
            status_code=401,
            code=exc.code,
            message=exc.message,
        ) from exc


def get_current_user(
    db: Session = Depends(get_db),
    token_payload: AccessTokenPayload = Depends(get_current_token_payload),
) -> User:
    user = db.get(User, token_payload.user_id)
    if not user or not user.is_active:
        raise ApiError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="Authentication is required.",
        )
    if user.is_blocked:
        raise ApiError(
            status_code=403,
            code="FORBIDDEN",
            message="User is blocked.",
        )
    if user.role != token_payload.role:
        raise ApiError(
            status_code=403,
            code="FORBIDDEN",
            message="Token role does not match user role.",
        )
    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.user_id


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
