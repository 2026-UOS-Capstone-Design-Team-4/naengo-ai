from app.api.v1.openapi.errors import (
    FORBIDDEN_RESPONSE,
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)
from app.api.v1.openapi.examples import (
    USER_RECIPE_REPORT_EXAMPLE,
    USER_RECIPE_REPORT_LIST_RESPONSE_EXAMPLE,
)

USER_RECIPE_REPORT_NOT_FOUND_RESPONSE = error_response(
    "사용자 레시피 신고를 찾을 수 없습니다.",
    "USER_RECIPE_REPORT_NOT_FOUND",
    "사용자 레시피 신고를 찾을 수 없습니다.",
)

INVALID_CURSOR_RESPONSE = error_response(
    "커서 값이 올바르지 않습니다.",
    "INVALID_CURSOR",
    "Cursor is invalid.",
)

GET_ADMIN_USER_RECIPE_REPORTS_SUMMARY = "[관리자] 사용자 레시피 신고 목록 조회"
GET_ADMIN_USER_RECIPE_REPORTS_DESCRIPTION = r"""
사용자 레시피 신고 검토 큐를 조회합니다.

- 최신순(`report_id` 내림차순)으로 반환합니다.
- `status`, 신고 대상 레시피, 신고자, 레시피 작성자로 필터링할 수 있습니다.
- `cursor`는 이전 응답의 `next_cursor`를 그대로 전달하는 인코딩 커서입니다.
- 첫 페이지는 `cursor`를 비워서 요청합니다.
"""

GET_ADMIN_USER_RECIPE_REPORTS_RESPONSES = {
    200: {
        "description": "사용자 레시피 신고 목록",
        "content": {
            "application/json": {"example": USER_RECIPE_REPORT_LIST_RESPONSE_EXAMPLE}
        },
    },
    400: INVALID_CURSOR_RESPONSE,
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_ADMIN_USER_RECIPE_REPORT_SUMMARY = "[관리자] 사용자 레시피 신고 상세 조회"
GET_ADMIN_USER_RECIPE_REPORT_DESCRIPTION = r"""
사용자 레시피 신고 하나를 조회합니다.
"""

GET_ADMIN_USER_RECIPE_REPORT_RESPONSES = {
    200: {
        "description": "사용자 레시피 신고 상세",
        "content": {"application/json": {"example": USER_RECIPE_REPORT_EXAMPLE}},
    },
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    404: USER_RECIPE_REPORT_NOT_FOUND_RESPONSE,
}

PATCH_ADMIN_USER_RECIPE_REPORT_SUMMARY = "[관리자] 사용자 레시피 신고 처리"
PATCH_ADMIN_USER_RECIPE_REPORT_DESCRIPTION = r"""
사용자 레시피 신고의 처리 상태와 검토 메모를 수정합니다.

- `status`가 변경되면 `reviewed_by`, `reviewed_at`을 기록합니다.
- 신고 처리 자체는 레시피 노출 상태를 자동 변경하지 않습니다.
- 레시피 비활성화 같은 후속 조치는 별도 admin API에서 수행합니다.
"""

PATCH_ADMIN_USER_RECIPE_REPORT_RESPONSES = {
    200: {
        "description": "처리된 사용자 레시피 신고",
        "content": {"application/json": {"example": USER_RECIPE_REPORT_EXAMPLE}},
    },
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    404: USER_RECIPE_REPORT_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}
