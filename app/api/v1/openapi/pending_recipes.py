from app.api.v1.openapi.errors import VALIDATION_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import PENDING_RECIPE_EXAMPLE

PENDING_RECIPE_NOT_FOUND_RESPONSE = error_response(
    "제출 레시피를 찾을 수 없습니다.",
    "PENDING_RECIPE_NOT_FOUND",
    "제출 레시피를 찾을 수 없습니다.",
)

USER_NOT_FOUND_RESPONSE = error_response(
    "사용자를 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "사용자를 찾을 수 없습니다.",
)

GET_PENDING_RECIPES_SUMMARY = "제출 레시피 목록 조회"
GET_PENDING_RECIPES_DESCRIPTION = r"""
현재 사용자가 제출한 레시피 목록을 반환합니다.

- 최신순(`created_at` 내림차순)으로 반환합니다.
- 제출 레시피는 정식 `recipes`에 바로 들어가지 않고 관리자 검수를 기다립니다.
- 사용자가 삭제하면 실제 삭제 대신 `is_active = false`로 변경합니다.
"""

GET_PENDING_RECIPES_RESPONSES = {
    200: {
        "description": "제출 레시피 목록",
        "content": {"application/json": {"example": [PENDING_RECIPE_EXAMPLE]}},
    },
}

GET_PENDING_RECIPE_SUMMARY = "제출 레시피 단건 조회"
GET_PENDING_RECIPE_DESCRIPTION = r"""
제출한 레시피 하나를 조회합니다.

본인이 제출한 레시피만 조회할 수 있습니다.
"""

GET_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "제출 레시피 상세",
        "content": {"application/json": {"example": PENDING_RECIPE_EXAMPLE}},
    },
    404: PENDING_RECIPE_NOT_FOUND_RESPONSE,
}

POST_PENDING_RECIPE_SUMMARY = "레시피 제출"
POST_PENDING_RECIPE_DESCRIPTION = r"""
사용자가 작성한 레시피를 제출합니다.

제출 레시피는 `PENDING` 상태로 저장되고 관리자가 검수 후 승인하거나 거절합니다.

**필드**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `title` | string | ✓ | 제출 레시피 제목 |
| `submission_text` | string | ✓ | 사용자가 처음 제출한 원문 설명 |

검수용 `draft_payload`와 `ai_suggested_patch`는 빈 기본 구조로 초기화합니다.
"""

POST_PENDING_RECIPE_RESPONSES = {
    201: {
        "description": "제출 성공",
        "content": {"application/json": {"example": PENDING_RECIPE_EXAMPLE}},
    },
    404: USER_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

DELETE_PENDING_RECIPE_SUMMARY = "제출 레시피 삭제"
DELETE_PENDING_RECIPE_DESCRIPTION = r"""
제출한 레시피를 삭제합니다.

현재 구현은 물리 삭제가 아니라 `is_active = false`로 변경합니다.
본인이 제출한 레시피만 삭제할 수 있습니다.
"""

DELETE_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "삭제 성공",
        "content": {"application/json": {"example": {"message": "레시피가 삭제되었습니다."}}},
    },
    404: PENDING_RECIPE_NOT_FOUND_RESPONSE,
}
