from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def error_payload(
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
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details),
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return error_response(
            exc.status_code,
            exc.code,
            exc.message,
            exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        fields = [
            {
                "name": ".".join(str(part) for part in error["loc"]),
                "reason": error["msg"],
            }
            for error in exc.errors()
        ]
        return error_response(
            422,
            "VALIDATION_FAILED",
            "Request validation failed.",
            {"fields": fields},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        if isinstance(detail, dict):
            code = str(detail.get("code") or _default_code(exc.status_code))
            message = str(detail.get("message") or _default_message(exc.status_code))
            details = detail.get("details")
            return error_response(
                exc.status_code,
                code,
                message,
                details if isinstance(details, dict) else {},
            )
        return error_response(
            exc.status_code,
            _default_code(exc.status_code),
            str(detail) if detail else _default_message(exc.status_code),
        )


def _default_code(status_code: int) -> str:
    return {
        400: "VALIDATION_FAILED",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "UPSTREAM_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }.get(status_code, "INTERNAL_ERROR")


def _default_message(status_code: int) -> str:
    return {
        400: "Request is invalid.",
        401: "Authentication is required.",
        403: "Permission denied.",
        404: "Resource not found.",
        409: "Request conflicts with the current state.",
        422: "Request could not be processed.",
        429: "Rate limit exceeded.",
        500: "Internal server error.",
        502: "Upstream provider error.",
        503: "Service is unavailable.",
    }.get(status_code, "Internal server error.")
