from app.api.v1.openapi.errors import (
    FORBIDDEN_RESPONSE,
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)
from app.api.v1.openapi.examples import (
    RECIPE_SOURCE_DETAIL_EXAMPLE,
    RECIPE_SOURCE_IMPORT_ACCEPTED_EXAMPLE,
    RECIPE_SOURCE_LIST_RESPONSE_EXAMPLE,
)

ADMIN_RECIPE_SOURCE_AUTH_RESPONSES = {
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
}

RECIPE_SOURCE_NOT_FOUND_RESPONSE = error_response(
    "수집 소스를 찾을 수 없습니다.",
    "RECIPE_SOURCE_NOT_FOUND",
    "소스를 찾을 수 없습니다.",
)

RECIPE_SOURCE_CONFLICT_RESPONSE = error_response(
    "현재 상태와 요청이 충돌합니다.",
    "CONFLICT",
    "현재 상태에서는 요청을 처리할 수 없습니다.",
)

RECIPE_SOURCE_NOT_IMPORTABLE_RESPONSE = error_response(
    "import 가능한 lifecycle 상태가 아닙니다.",
    "RECIPE_SOURCE_NOT_IMPORTABLE",
    "APPROVED + NOT_IMPORTED 상태인 소스만 import할 수 있습니다.",
    {
        "current": {
            "review_status": "PENDING",
            "import_status": "NOT_IMPORTED",
        },
        "required": {
            "review_status": "APPROVED",
            "import_status": "NOT_IMPORTED",
        },
    },
)

GET_RECIPE_SOURCES_SUMMARY = "[관리자] 레시피 수집 소스 목록 조회"
GET_RECIPE_SOURCES_DESCRIPTION = r"""
수집된 원본 레시피 소스 목록을 커서 기반 페이지네이션으로 조회합니다.

관리자는 이 목록에서 수집, 파싱, 검수, import 상태를 확인하고 후속 작업을 수행합니다.

**필터**:

| 파라미터 | 설명 |
|----------|------|
| `parse_status` | 파싱 상태 |
| `review_status` | 검수 상태 |
| `import_status` | import 상태 |
| `source_site` | 원본 사이트 |
| `cursor` | 이전 응답의 `next_cursor` |
| `limit` | 조회 개수. 기본 20, 최대 100 |
"""

GET_RECIPE_SOURCES_RESPONSES = {
    200: {
        "description": "수집 소스 목록",
        "content": {
            "application/json": {"example": RECIPE_SOURCE_LIST_RESPONSE_EXAMPLE}
        },
    },
    422: VALIDATION_ERROR_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}

GET_RECIPE_SOURCE_SUMMARY = "[관리자] 레시피 수집 소스 상세 조회"
GET_RECIPE_SOURCE_DESCRIPTION = r"""
수집 소스와 staging extraction 데이터를 함께 조회합니다.

`recipe_source_extractions`, 재료, 조리 단계, label 정보를 한 번에 확인할 수 있습니다.
"""

GET_RECIPE_SOURCE_RESPONSES = {
    200: {
        "description": "수집 소스 상세",
        "content": {"application/json": {"example": RECIPE_SOURCE_DETAIL_EXAMPLE}},
    },
    404: RECIPE_SOURCE_NOT_FOUND_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}

PATCH_RECIPE_SOURCE_SUMMARY = "[관리자] 레시피 수집 소스 수정"
PATCH_RECIPE_SOURCE_DESCRIPTION = r"""
관리자가 extraction 또는 검수 관련 상태를 보정합니다.

- `extraction`을 전달하면 staging extraction을 교체하고 `parse_status`를 `PARSED`로 갱신합니다.
- `validation_errors`, `parse_status`, `review_status`는 운영 검수 화면에서 직접 보정할 수 있습니다.
- import 완료 후 원본을 되돌리는 용도로 사용하지 않습니다.
"""

PATCH_RECIPE_SOURCE_RESPONSES = {
    200: {
        "description": "수정된 수집 소스",
        "content": {"application/json": {"example": RECIPE_SOURCE_DETAIL_EXAMPLE}},
    },
    404: RECIPE_SOURCE_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}

APPROVE_RECIPE_SOURCE_SUMMARY = "[관리자] 레시피 수집 소스 승인"
APPROVE_RECIPE_SOURCE_DESCRIPTION = r"""
수집 소스의 extraction을 검증하고 import 가능한 상태로 승인합니다.

검증 실패 시 DB에 저장하지 않고 거절하는 것이 아니라, `validation_errors`를 갱신하고
`parse_status = REVIEW_REQUIRED`, `review_status = PENDING` 상태로 되돌립니다.
"""

APPROVE_RECIPE_SOURCE_RESPONSES = {
    200: {
        "description": "승인 또는 재검수 상태로 갱신된 수집 소스",
        "content": {"application/json": {"example": RECIPE_SOURCE_DETAIL_EXAMPLE}},
    },
    404: RECIPE_SOURCE_NOT_FOUND_RESPONSE,
    409: RECIPE_SOURCE_CONFLICT_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}

REJECT_RECIPE_SOURCE_SUMMARY = "[관리자] 레시피 수집 소스 거절"
REJECT_RECIPE_SOURCE_DESCRIPTION = r"""
수집 소스를 거절 상태로 변경하고 거절 사유를 `validation_errors`에 기록합니다.

이미 import된 소스는 거절할 수 없습니다.
"""

REJECT_RECIPE_SOURCE_RESPONSES = {
    200: {
        "description": "거절된 수집 소스",
        "content": {"application/json": {"example": RECIPE_SOURCE_DETAIL_EXAMPLE}},
    },
    404: RECIPE_SOURCE_NOT_FOUND_RESPONSE,
    409: RECIPE_SOURCE_CONFLICT_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}

IMPORT_RECIPE_SOURCE_SUMMARY = "[관리자] 승인된 수집 소스 import"
IMPORT_RECIPE_SOURCE_DESCRIPTION = r"""
승인된 수집 소스를 정식 레시피 테이블로 승격하는 import 작업을 시작합니다.

이 작업은 FastAPI `BackgroundTasks`로 실행되며 API는 즉시 `202 Accepted`를 반환합니다.
Phase 1에서는 별도 job table 없이 `recipe_sources.import_status`로 결과를 추적합니다.

import 가능한 조건:

- `review_status = APPROVED`
- `import_status = NOT_IMPORTED`
"""

IMPORT_RECIPE_SOURCE_RESPONSES = {
    202: {
        "description": "import 작업 접수",
        "content": {
            "application/json": {"example": RECIPE_SOURCE_IMPORT_ACCEPTED_EXAMPLE}
        },
    },
    404: RECIPE_SOURCE_NOT_FOUND_RESPONSE,
    409: RECIPE_SOURCE_NOT_IMPORTABLE_RESPONSE,
    **ADMIN_RECIPE_SOURCE_AUTH_RESPONSES,
}
