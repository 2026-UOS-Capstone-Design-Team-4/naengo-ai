from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.errors import ApiError
from app.api.v1 import deps
from app.models.user import User, UserProfile
from app.services.auth_service import AuthService, TokenValidationError

SECRET = "test-secret-for-hs512-must-be-at-least-sixty-four-bytes-long!!!!"
ALGORITHM = "HS512"


class FakeDb:
    def __init__(self, user=None, profile=None):
        self.user = user
        self.profile = profile
        self.added = []
        self.committed = False
        self.refreshed = []

    def get(self, model, _user_id):
        if model is UserProfile:
            return self.profile
        return self.user

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, User):
            self.user = obj
        if isinstance(obj, UserProfile):
            self.profile = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def _token(
    *,
    sub="7",
    role="USER",
    secret=SECRET,
    algorithm=ALGORITHM,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> str:
    now = issued_at or datetime.now(UTC)
    exp = expires_at or now + timedelta(days=1)
    return jwt.encode(
        {
            "sub": sub,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        },
        secret,
        algorithm=algorithm,
    )


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _user(user_id=7, role="USER", is_active=True, is_blocked=False):
    return SimpleNamespace(
        user_id=user_id,
        role=role,
        is_active=is_active,
        is_blocked=is_blocked,
    )


def test_auth_service_decodes_valid_hs512_access_token():
    payload = AuthService(SECRET, ALGORITHM).decode_access_token(_token())

    assert payload.user_id == 7
    assert payload.role == "USER"


def test_auth_service_rejects_expired_access_token():
    token = _token(
        issued_at=datetime.now(UTC) - timedelta(days=2),
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    with pytest.raises(TokenValidationError) as exc:
        AuthService(SECRET, ALGORITHM).decode_access_token(token)

    assert exc.value.code == "TOKEN_EXPIRED"


def test_auth_service_rejects_non_hs512_algorithm():
    token = _token(algorithm="HS256")

    with pytest.raises(TokenValidationError) as exc:
        AuthService(SECRET, ALGORITHM).decode_access_token(token)

    assert exc.value.code == "INVALID_TOKEN"


def test_current_token_payload_requires_bearer_token():
    with pytest.raises(ApiError) as exc:
        deps.get_current_token_payload(None)

    assert exc.value.status_code == 401
    assert exc.value.code == "UNAUTHENTICATED"


def test_dev_auth_disabled_allows_missing_bearer_token(monkeypatch):
    monkeypatch.setattr(deps, "APP_ENV", "dev")
    monkeypatch.setattr(deps, "AUTH_DISABLED", True)
    monkeypatch.setattr(deps, "DEV_AUTH_USER_ID", 42)
    monkeypatch.setattr(deps, "DEV_AUTH_ROLE", "ADMIN")

    payload = deps.get_current_token_payload(None)

    assert payload.user_id == 42
    assert payload.role == "ADMIN"


def test_auth_disabled_outside_dev_fails_closed(monkeypatch):
    monkeypatch.setattr(deps, "APP_ENV", "prod")
    monkeypatch.setattr(deps, "AUTH_DISABLED", True)

    with pytest.raises(ApiError) as exc:
        deps.get_current_token_payload(None)

    assert exc.value.status_code == 503
    assert exc.value.code == "SERVICE_UNAVAILABLE"


def test_current_token_payload_uses_configured_secret(monkeypatch):
    monkeypatch.setattr(deps, "JWT_SECRET_KEY", SECRET)
    monkeypatch.setattr(deps, "JWT_ALGORITHM", ALGORITHM)

    payload = deps.get_current_token_payload(_credentials(_token()))

    assert payload.user_id == 7
    assert payload.role == "USER"


def test_current_user_rejects_missing_user():
    payload = AuthService(SECRET, ALGORITHM).decode_access_token(_token())

    with pytest.raises(ApiError) as exc:
        deps.get_current_user(FakeDb(user=None), payload)

    assert exc.value.status_code == 401


def test_current_user_rejects_blocked_user():
    payload = AuthService(SECRET, ALGORITHM).decode_access_token(_token())

    with pytest.raises(ApiError) as exc:
        deps.get_current_user(FakeDb(user=_user(is_blocked=True)), payload)

    assert exc.value.status_code == 403


def test_current_user_rejects_role_mismatch():
    payload = AuthService(SECRET, ALGORITHM).decode_access_token(_token(role="ADMIN"))

    with pytest.raises(ApiError) as exc:
        deps.get_current_user(FakeDb(user=_user(role="USER")), payload)

    assert exc.value.status_code == 403


def test_dev_current_user_creates_local_user_and_profile(monkeypatch):
    monkeypatch.setattr(deps, "APP_ENV", "dev")
    monkeypatch.setattr(deps, "AUTH_DISABLED", True)
    payload = deps.AccessTokenPayload(
        user_id=42,
        role="ADMIN",
        issued_at=0,
        expires_at=0,
    )
    db = FakeDb()

    user = deps.get_current_user(db, payload)

    assert user.user_id == 42
    assert user.role == "ADMIN"
    assert user.is_active is True
    assert user.is_blocked is False
    assert db.profile.user_id == 42
    assert db.profile.user_input == []
    assert db.committed is True
    assert db.refreshed == [user]


def test_current_user_id_returns_authenticated_user_id():
    user = _user(user_id=7)

    assert deps.get_current_user_id(user) == 7


def test_require_admin_allows_admin_user():
    user = _user(role="ADMIN")

    assert deps.require_admin(user) is user


def test_dev_require_admin_uses_configured_role(monkeypatch):
    monkeypatch.setattr(deps, "APP_ENV", "dev")
    monkeypatch.setattr(deps, "AUTH_DISABLED", True)
    monkeypatch.setattr(deps, "DEV_AUTH_ROLE", "ADMIN")
    user = _user(role="USER")

    assert deps.require_admin(user) is user


def test_require_admin_rejects_user_role():
    with pytest.raises(ApiError) as exc:
        deps.require_admin(_user(role="USER"))

    assert exc.value.status_code == 403
