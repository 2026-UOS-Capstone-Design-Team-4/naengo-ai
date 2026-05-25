from dataclasses import dataclass
from typing import Any, Literal

import jwt

TokenRole = Literal["USER", "ADMIN"]


class TokenValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: int
    role: TokenRole
    issued_at: int
    expires_at: int


class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS512") -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "role", "iat", "exp"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenValidationError(
                "TOKEN_EXPIRED",
                "Access token has expired.",
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise TokenValidationError(
                "INVALID_TOKEN",
                "Access token is invalid.",
            ) from exc

        return _parse_payload(payload)


def _parse_payload(payload: dict[str, Any]) -> AccessTokenPayload:
    try:
        user_id = int(payload["sub"])
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError(
            "INVALID_TOKEN",
            "Access token claims are invalid.",
        ) from exc

    role = payload.get("role")
    if role not in {"USER", "ADMIN"}:
        raise TokenValidationError(
            "INVALID_TOKEN",
            "Access token role is invalid.",
        )

    return AccessTokenPayload(
        user_id=user_id,
        role=role,
        issued_at=issued_at,
        expires_at=expires_at,
    )
