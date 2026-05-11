from app.api.v1.docs.examples import (
    RECIPE_DETAIL_RESPONSE_EXAMPLE,
    RECIPE_LIST_RESPONSE_EXAMPLE,
    RECIPE_STATS_RESPONSE_EXAMPLE,
)

GET_RECIPES_SUMMARY = "레시피 목록 조회"
GET_RECIPES_DESCRIPTION = r"""
전체 레시피 목록을 커서 기반 페이지네이션으로 반환합니다.

**정렬 기준**:

| `sort` 값 | 설명 |
|-----------|------|
| `latest` | 최신순 (기본값) |
| `likes` | 좋아요 많은순 |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `sort` | string | `latest` | 정렬 기준 |
| `cursor` | string | 없음 | 이전 응답의 `next_cursor` 값 (첫 페이지는 생략) |
| `limit` | int | `20` | 한 번에 가져올 개수 (최대 100) |

**응답 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `items` | Recipe[] | 레시피 목록 |
| `next_cursor` | string \| null | 다음 페이지 커서 (`null`이면 마지막 페이지) |
| `has_next` | bool | 다음 페이지 존재 여부 |
"""

GET_RECIPES_RESPONSES = {
    200: {
        "description": "레시피 목록",
        "content": {"application/json": {"example": RECIPE_LIST_RESPONSE_EXAMPLE}},
    }
}

GET_RECIPE_SUMMARY = "레시피 단건 조회"
GET_RECIPE_DESCRIPTION = r"""
레시피 ID로 레시피 상세 정보를 조회합니다.

- 삭제된 레시피는 조회할 수 없습니다.
- 현재 사용자의 좋아요(`is_liked`) 및 스크랩(`is_scrapped`) 여부를 함께 반환합니다.
"""

GET_RECIPE_RESPONSES = {
    200: {
        "description": "레시피 상세",
        "content": {"application/json": {"example": RECIPE_DETAIL_RESPONSE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
}

POST_LIKE_SUMMARY = "레시피 좋아요"
POST_LIKE_DESCRIPTION = r"""
레시피에 좋아요를 추가합니다.

- 이미 좋아요를 누른 경우 `409`를 반환합니다.
- 성공 시 업데이트된 좋아요·스크랩 수를 반환합니다.
"""

POST_LIKE_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
    409: {"description": "이미 좋아요를 눌렀습니다."},
}

DELETE_LIKE_SUMMARY = "레시피 좋아요 취소"
DELETE_LIKE_DESCRIPTION = r"""
레시피 좋아요를 취소합니다.

- 좋아요를 누르지 않은 경우 `409`를 반환합니다.
- 성공 시 업데이트된 좋아요·스크랩 수를 반환합니다.
"""

DELETE_LIKE_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
    409: {"description": "좋아요를 누르지 않았습니다."},
}

POST_SCRAP_SUMMARY = "레시피 스크랩"
POST_SCRAP_DESCRIPTION = r"""
레시피를 스크랩(북마크)합니다.

- 이미 스크랩한 경우 `409`를 반환합니다.
- 성공 시 업데이트된 좋아요·스크랩 수를 반환합니다.
"""

POST_SCRAP_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
    409: {"description": "이미 스크랩한 레시피입니다."},
}

DELETE_SCRAP_SUMMARY = "레시피 스크랩 취소"
DELETE_SCRAP_DESCRIPTION = r"""
레시피 스크랩을 취소합니다.

- 스크랩하지 않은 경우 `409`를 반환합니다.
- 성공 시 업데이트된 좋아요·스크랩 수를 반환합니다.
"""

DELETE_SCRAP_RESPONSES = {
    200: {
        "description": "업데이트된 통계",
        "content": {"application/json": {"example": RECIPE_STATS_RESPONSE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
    409: {"description": "스크랩하지 않은 레시피입니다."},
}
