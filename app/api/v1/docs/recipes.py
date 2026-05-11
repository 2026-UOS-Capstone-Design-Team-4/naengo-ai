from app.api.v1.docs.examples import RECIPE_LIST_RESPONSE_EXAMPLE

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
