from app.api.v1.openapi.errors import VALIDATION_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import (
    RECIPE_DETAIL_RESPONSE_EXAMPLE,
    RECIPE_LIST_RESPONSE_EXAMPLE,
    RECIPE_STATS_RESPONSE_EXAMPLE,
)

RECIPE_NOT_FOUND_RESPONSE = error_response(
    "레시피를 찾을 수 없습니다.",
    "RECIPE_NOT_FOUND",
    "레시피를 찾을 수 없습니다.",
)

INVALID_CURSOR_RESPONSE = error_response(
    "커서 값이 올바르지 않습니다.",
    "INVALID_CURSOR",
    "Cursor is invalid.",
)

ALREADY_LIKED_RESPONSE = error_response(
    "이미 좋아요를 누른 레시피입니다.",
    "ALREADY_LIKED",
    "이미 좋아요를 누른 레시피입니다.",
)

NOT_LIKED_RESPONSE = error_response(
    "좋아요를 누르지 않았습니다.",
    "NOT_LIKED",
    "좋아요를 누르지 않았습니다.",
)

ALREADY_SCRAPPED_RESPONSE = error_response(
    "이미 스크랩한 레시피입니다.",
    "ALREADY_SCRAPPED",
    "이미 스크랩한 레시피입니다.",
)

NOT_SCRAPPED_RESPONSE = error_response(
    "스크랩하지 않은 레시피입니다.",
    "NOT_SCRAPPED",
    "스크랩하지 않은 레시피입니다.",
)

GET_RECIPES_SUMMARY = "레시피 목록 조회"
GET_RECIPES_DESCRIPTION = r"""
전체 레시피 목록을 커서 기반 페이지네이션으로 반환합니다.

**정렬 기준**

| `sort` 값 | 설명 |
|-----------|------|
| `latest` | 최신순. 기본값입니다. |
| `likes` | 좋아요 많은 순입니다. |
| `scraps` | 스크랩/북마크 많은 순입니다. |

**쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `sort` | string | `latest` | 정렬 기준입니다. `latest`, `likes`, `scraps` 중 하나를 사용합니다. |
| `cursor` | string | 없음 | 이전 응답의 `next_cursor` 값입니다. base64url로 인코딩된 JSON입니다. |
| `limit` | int | `20` | 한 번에 가져올 개수입니다. 최소 1, 최대 100입니다. |

**커서 형식**

`next_cursor`는 클라이언트가 해석하지 않고 다음 요청의 `cursor`에 그대로 전달하는 값입니다.
내부 payload는 정렬 기준에 따라 다음 JSON을 base64url로 인코딩합니다.

```json
{"sort":"latest","recipe_id":42}
{"sort":"likes","count":15,"recipe_id":42}
{"sort":"scraps","count":8,"recipe_id":42}
```

현재 요청의 `sort`와 맞지 않는 cursor 또는 잘못된 cursor를 보내면
`400 INVALID_CURSOR`를 반환합니다.

응답의 각 레시피에는 현재 사용자 기준 `is_liked`, `is_scrapped`가 포함됩니다.
"""

GET_RECIPES_RESPONSES = {
    200: {
        "description": "레시피 목록",
        "content": {"application/json": {"example": RECIPE_LIST_RESPONSE_EXAMPLE}},
    },
    400: INVALID_CURSOR_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_RECIPE_SUMMARY = "레시피 상세 조회"
GET_RECIPE_DESCRIPTION = r"""
레시피 ID로 상세 정보를 조회합니다.

- 삭제되었거나 비활성화된 레시피는 조회할 수 없습니다.
- 현재 사용자 기준 좋아요 여부(`is_liked`)와 스크랩 여부(`is_scrapped`)를 함께 반환합니다.
"""

GET_RECIPE_RESPONSES = {
    200: {
        "description": "레시피 상세",
        "content": {"application/json": {"example": RECIPE_DETAIL_RESPONSE_EXAMPLE}},
    },
    404: RECIPE_NOT_FOUND_RESPONSE,
}

POST_LIKE_SUMMARY = "레시피 좋아요"
POST_LIKE_DESCRIPTION = r"""
레시피에 좋아요를 추가합니다.

- 이미 좋아요를 누른 경우 `409 ALREADY_LIKED`를 반환합니다.
- 성공하면 변경된 좋아요/스크랩 집계를 반환합니다.
"""

POST_LIKE_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: RECIPE_NOT_FOUND_RESPONSE,
    409: ALREADY_LIKED_RESPONSE,
}

DELETE_LIKE_SUMMARY = "레시피 좋아요 취소"
DELETE_LIKE_DESCRIPTION = r"""
레시피 좋아요를 취소합니다.

- 좋아요를 누르지 않은 경우 `409 NOT_LIKED`를 반환합니다.
- 성공하면 변경된 좋아요/스크랩 집계를 반환합니다.
"""

DELETE_LIKE_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: RECIPE_NOT_FOUND_RESPONSE,
    409: NOT_LIKED_RESPONSE,
}

POST_SCRAP_SUMMARY = "레시피 스크랩"
POST_SCRAP_DESCRIPTION = r"""
레시피를 스크랩 목록에 추가합니다.

- 이미 스크랩한 경우 `409 ALREADY_SCRAPPED`를 반환합니다.
- 성공하면 변경된 좋아요/스크랩 집계를 반환합니다.
"""

POST_SCRAP_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: RECIPE_NOT_FOUND_RESPONSE,
    409: ALREADY_SCRAPPED_RESPONSE,
}

DELETE_SCRAP_SUMMARY = "레시피 스크랩 취소"
DELETE_SCRAP_DESCRIPTION = r"""
레시피 스크랩을 취소합니다.

- 스크랩하지 않은 경우 `409 NOT_SCRAPPED`를 반환합니다.
- 성공하면 변경된 좋아요/스크랩 집계를 반환합니다.
"""

DELETE_SCRAP_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: RECIPE_NOT_FOUND_RESPONSE,
    409: NOT_SCRAPPED_RESPONSE,
}
