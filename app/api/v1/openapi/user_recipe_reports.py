from app.api.v1.openapi.errors import (
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)
from app.api.v1.openapi.examples import USER_RECIPE_REPORT_EXAMPLE

USER_RECIPE_REPORT_NOT_FOUND_RESPONSE = error_response(
    "신고 가능한 사용자 레시피를 찾을 수 없습니다.",
    "USER_RECIPE_NOT_FOUND",
    "신고 가능한 사용자 레시피를 찾을 수 없습니다.",
)

ALREADY_REPORTED_RESPONSE = error_response(
    "이미 신고한 사용자 레시피입니다.",
    "ALREADY_REPORTED",
    "이미 신고한 사용자 레시피입니다.",
)

CANNOT_REPORT_OWN_RECIPE_RESPONSE = error_response(
    "본인이 작성한 레시피는 신고할 수 없습니다.",
    "CANNOT_REPORT_OWN_RECIPE",
    "본인이 작성한 레시피는 신고할 수 없습니다.",
)

POST_USER_RECIPE_REPORT_SUMMARY = "사용자 레시피 신고"
POST_USER_RECIPE_REPORT_DESCRIPTION = r"""
공개된 사용자 제출 레시피를 신고합니다.

- `APPROVED` 상태이고 활성 상태인 사용자 레시피만 신고할 수 있습니다.
- 본인이 작성한 레시피는 신고할 수 없습니다.
- 같은 사용자는 같은 레시피를 한 번만 신고할 수 있습니다.
- 신고는 레시피를 즉시 비노출하지 않고 관리자 검토 큐에 저장됩니다.

`reason` 값:

- `INAPPROPRIATE`: 부적절한 내용
- `COPYRIGHT`: 저작권/무단 도용
- `SPAM`: 광고/스팸
- `DANGEROUS`: 위험한 조리법/안전 문제
- `FALSE_INFO`: 잘못된 정보
- `OTHER`: 기타
"""

POST_USER_RECIPE_REPORT_RESPONSES = {
    201: {
        "description": "신고 접수 완료",
        "content": {"application/json": {"example": USER_RECIPE_REPORT_EXAMPLE}},
    },
    401: UNAUTHENTICATED_RESPONSE,
    404: USER_RECIPE_REPORT_NOT_FOUND_RESPONSE,
    409: ALREADY_REPORTED_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}
