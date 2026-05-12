from app.api.v1.docs.examples import PENDING_RECIPE_REVIEWED_EXAMPLE

PATCH_ADMIN_PENDING_RECIPE_SUMMARY = "[관리자] 제출 레시피 상태 수정"
PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION = r"""
제출된 레시피의 내용과 검토 상태를 수정합니다.

- 전달하지 않은 필드는 변경하지 않습니다.
- `status`가 변경되면 `reviewed_at`을 현재 시각으로 기록합니다.
- `status`를 `APPROVED`로 바꾸면 정식 레시피(`Recipe`)로 승격합니다.
- 승인 승격 시 `RecipeStats`와 검색용 embedding을 함께 생성합니다.
- 승인에 필요한 필수 레시피 필드가 부족하면 `400`을 반환합니다.

**승인 필수 필드**:

`title`, `description`, `ingredients`, `ingredients_raw`, `instructions`,
`servings`, `cooking_time`, `difficulty`, `category`
"""

PATCH_ADMIN_PENDING_RECIPE_RESPONSES = {
    200: {
        "description": "수정된 제출 레시피",
        "content": {
            "application/json": {"example": PENDING_RECIPE_REVIEWED_EXAMPLE}
        },
    },
    400: {"description": "승인에 필요한 필수 필드가 부족합니다."},
    404: {"description": "레시피를 찾을 수 없습니다."},
}
