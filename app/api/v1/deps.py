from typing import cast

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import (
    APP_ENV,
    AUTH_DISABLED,
    DEV_AUTH_ROLE,
    DEV_AUTH_USER_ID,
    INTERNAL_API_SECRET,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.services.auth_service import (
    AccessTokenPayload,
    AuthService,
    TokenRole,
    TokenValidationError,
)

bearer_scheme = HTTPBearer(auto_error=False)
_DEV_ENV_NAMES = {"dev", "development", "local"}


def _is_dev_environment() -> bool:
    return APP_ENV.strip().lower() in _DEV_ENV_NAMES


def _is_dev_auth_disabled() -> bool:
    return AUTH_DISABLED and _is_dev_environment()


def _get_dev_auth_role() -> TokenRole:
    if DEV_AUTH_ROLE not in {"USER", "ADMIN"}:
        raise ApiError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="DEV_AUTH_ROLE must be USER or ADMIN.",
        )
    return cast(TokenRole, DEV_AUTH_ROLE)


def _get_dev_token_payload() -> AccessTokenPayload:
    return AccessTokenPayload(
        user_id=DEV_AUTH_USER_ID,
        role=_get_dev_auth_role(),
        issued_at=0,
        expires_at=0,
    )


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccessTokenPayload:
    if AUTH_DISABLED and not _is_dev_environment():
        raise ApiError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="AUTH_DISABLED can only be used when APP_ENV is dev/local.",
        )
    if _is_dev_auth_disabled():
        return _get_dev_token_payload()
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
    if _is_dev_auth_disabled():
        return _ensure_dev_user(db, token_payload, user)
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


def _ensure_dev_user(
    db: Session,
    token_payload: AccessTokenPayload,
    user: User | None,
) -> User:
    must_commit = False

    if user is None:
        user = User(
            user_id=token_payload.user_id,
            username=f"dev_user_{token_payload.user_id}",
            password_hash=None,
            nickname=f"Dev User {token_payload.user_id}",
            role=token_payload.role,
            is_active=True,
            is_blocked=False,
        )
        db.add(user)
        must_commit = True

    profile = db.get(UserProfile, token_payload.user_id)
    if profile is None:
        db.add(
            UserProfile(
                user_id=token_payload.user_id,
                user_input=[],
                allergies=[],
                dietary_restrictions=[],
                preferred_ingredients=[],
                disliked_ingredients=[],
                preferred_categories=[],
                frequently_used_ingredients=[],
                taste_keywords=[],
                recent_recipe_ids=[],
            )
        )
        must_commit = True

    if must_commit:
        db.commit()
        db.refresh(user)

    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.user_id


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if _is_dev_auth_disabled():
        if _get_dev_auth_role() == "ADMIN":
            return current_user
        raise ApiError(
            status_code=403,
            code="FORBIDDEN",
            message="Admin permission is required.",
        )
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
