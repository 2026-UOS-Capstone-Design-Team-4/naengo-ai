from app.api.v1.docs.examples import PENDING_RECIPE_EXAMPLE

GET_PENDING_RECIPES_SUMMARY = "제출 레시피 목록 조회"
GET_PENDING_RECIPES_DESCRIPTION = r"""
현재 사용자가 제출한 레시피 목록을 반환합니다.

- 삭제 처리된 레시피(`is_active = false`)는 제외합니다.
- 최신순(`created_at` 내림차순)으로 반환합니다.
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

- 본인이 제출한 레시피만 조회할 수 있습니다.
- 삭제 처리된 레시피는 조회할 수 없습니다.
"""

GET_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "제출 레시피 상세",
        "content": {"application/json": {"example": PENDING_RECIPE_EXAMPLE}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
}

POST_PENDING_RECIPE_SUMMARY = "레시피 제출"
POST_PENDING_RECIPE_DESCRIPTION = r"""
사용자가 작성한 레시피를 제출합니다.

제출된 레시피는 `PENDING` 상태로 저장되고, 관리자가 검토 후 승인하거나 거절합니다.

**필수 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `title` | string | 레시피 제목 |
| `content` | string | 자유 형식 레시피 본문 |

나머지 구조화 필드는 선택값입니다. 다만 관리자가 `APPROVED`로 승인하려면 정식 레시피 생성에 필요한 필드가 채워져 있어야 합니다.
"""

POST_PENDING_RECIPE_RESPONSES = {
    201: {
        "description": "제출 성공",
        "content": {"application/json": {"example": PENDING_RECIPE_EXAMPLE}},
    },
    404: {"description": "사용자를 찾을 수 없습니다."},
}

DELETE_PENDING_RECIPE_SUMMARY = "제출 레시피 삭제"
DELETE_PENDING_RECIPE_DESCRIPTION = r"""
제출한 레시피를 삭제 처리합니다.

- 실제 데이터는 삭제하지 않고 `is_active`를 `false`로 변경합니다.
- 본인이 제출한 레시피만 삭제할 수 있습니다.
- 이미 삭제된 레시피에 요청하면 `404`를 반환합니다.
"""

DELETE_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "삭제 성공",
        "content": {"application/json": {"example": {"message": "레시피가 삭제되었습니다."}}},
    },
    404: {"description": "레시피를 찾을 수 없습니다."},
}
