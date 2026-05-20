from app.api.v1.openapi.errors import (
    FORBIDDEN_RESPONSE,
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)
from app.api.v1.openapi.examples import USER_RECIPE_REVIEWED_EXAMPLE

PENDING_RECIPE_NOT_FOUND_RESPONSE = error_response(
    "제출 레시피를 찾을 수 없습니다.",
    "PENDING_RECIPE_NOT_FOUND",
    "제출 레시피를 찾을 수 없습니다.",
)

INVALID_CURSOR_RESPONSE = error_response(
    "커서 값이 올바르지 않습니다.",
    "INVALID_CURSOR",
    "Cursor is invalid.",
)

GET_ADMIN_PENDING_RECIPES_SUMMARY = "[관리자] 제출 레시피 목록 조회"
GET_ADMIN_PENDING_RECIPES_DESCRIPTION = r"""
관리자가 사용자가 제출한 레시피 목록을 조회합니다.

목록은 최신 제출순(`pending_recipe_id` 내림차순)으로 반환합니다.
필요하면 상태, 사용자, 검색어로 검수 대상을 좁힐 수 있습니다.

**필터**

- `status`: 제출 레시피 검수 상태입니다. `PENDING`, `APPROVED`, `REJECTED`
- `is_active`: 사용자 삭제 여부를 포함한 활성 상태입니다.
- `user_id`: 특정 사용자가 제출한 레시피만 조회합니다.
- `q`: 제목과 원문(`submission_text`)에서 부분 검색합니다.

**페이지네이션**

- `cursor`는 이전 응답의 `next_cursor`를 그대로 전달하는 인코딩 커서입니다.
- 첫 페이지는 `cursor`를 비워서 요청합니다.
- 숫자 ID를 직접 넣거나 다른 목록의 커서를 섞어 쓰면 `400 INVALID_CURSOR`를 반환합니다.
"""

GET_ADMIN_PENDING_RECIPES_RESPONSES = {
    400: INVALID_CURSOR_RESPONSE,
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_ADMIN_PENDING_RECIPE_SUMMARY = "[관리자] 제출 레시피 상세 조회"
GET_ADMIN_PENDING_RECIPE_DESCRIPTION = r"""
관리자가 사용자가 제출한 레시피 하나를 조회합니다.

원문(`submission_text`), 검수 draft(`draft_payload`), AI 보정 후보(`ai_suggested_patch`),
검증 오류(`validation_errors`), 검수 결과를 함께 반환합니다.
"""

PATCH_ADMIN_PENDING_RECIPE_SUMMARY = "[관리자] 제출 레시피 상태 수정"
PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION = r"""
제출 레시피의 검수 내용과 상태를 수정합니다.

- 전달하지 않은 필드는 변경하지 않습니다.
- `status`가 변경되면 `reviewed_at`을 현재 시각으로 기록합니다.
- `status`를 `APPROVED`로 바꾸면 제출 레시피가 서비스에 노출 가능한 상태가 됩니다.
- 정식 레시피(`recipes`) import는 별도 작업으로 처리합니다.
- AI 보정 제안은 `ai_suggested_patch`에 저장하고, 관리자가 확인한 값만 `draft_payload`에 반영합니다.

**승인 필수 필드**

- `title`
- `draft_payload.description`
- `draft_payload.ingredients`
- `draft_payload.ingredients_raw`
- `draft_payload.instructions`
- `draft_payload.servings`
- `draft_payload.cooking_time_minutes`
- `draft_payload.difficulty`
- `draft_payload.category`
"""

PATCH_ADMIN_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "수정된 제출 레시피",
        "content": {
            "application/json": {"example": USER_RECIPE_REVIEWED_EXAMPLE}
        },
    },
    400: VALIDATION_ERROR_RESPONSE,
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    404: PENDING_RECIPE_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

DELETE_ADMIN_PENDING_RECIPE_SUMMARY = "[관리자] 비활성 제출 레시피 물리 삭제"
DELETE_ADMIN_PENDING_RECIPE_DESCRIPTION = r"""
`is_active = false`인 제출 레시피를 DB에서 물리 삭제합니다.

활성 제출건은 사용자 삭제/탈퇴 흐름을 먼저 거쳐야 하며, 관리자 API에서 바로 물리 삭제할 수 없습니다.
"""

DELETE_ADMIN_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "삭제 완료",
        "content": {
            "application/json": {"example": {"message": "제출 레시피가 삭제되었습니다."}}
        },
    },
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    404: PENDING_RECIPE_NOT_FOUND_RESPONSE,
    409: error_response(
        "활성 제출 레시피는 물리 삭제할 수 없습니다.",
        "PENDING_RECIPE_ACTIVE",
        "Active pending recipe cannot be hard-deleted.",
    ),
}
