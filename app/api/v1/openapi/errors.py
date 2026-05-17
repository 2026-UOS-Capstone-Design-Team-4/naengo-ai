from typing import Any


def error_example(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def error_response(
    description: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "example": error_example(code, message, details),
            }
        },
    }


VALIDATION_ERROR_RESPONSE = error_response(
    "요청 값이 유효하지 않습니다.",
    "VALIDATION_FAILED",
    "Request validation failed.",
    {
        "fields": [
            {
                "name": "query.limit",
                "reason": "Input should be greater than or equal to 1",
            }
        ]
    },
)

UNAUTHENTICATED_RESPONSE = error_response(
    "인증이 필요합니다.",
    "UNAUTHENTICATED",
    "Authentication is required.",
)

FORBIDDEN_RESPONSE = error_response(
    "권한이 없습니다.",
    "FORBIDDEN",
    "Admin permission is required.",
)

INTERNAL_ERROR_RESPONSE = error_response(
    "서버 내부 오류입니다.",
    "INTERNAL_ERROR",
    "Internal server error.",
)
