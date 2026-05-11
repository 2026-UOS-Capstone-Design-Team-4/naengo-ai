from app.api.v1.docs.examples import PENDING_RECIPE_REVIEWED_EXAMPLE

PATCH_ADMIN_PENDING_RECIPE_SUMMARY = "[관리자] 제출 레시피 상태 수정"
PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION = r"""
제출된 레시피의 내용과 검수 상태를 수정합니다.

- 전달하지 않은 필드는 변경하지 않습니다.
- `status`가 변경되면 `reviewed_at`이 현재 시각으로 기록됩니다.
- `status`를 `APPROVED`로 바꾸면 승인 레시피(`Recipe`)로 승격됩니다.
- 승인 승격 시 `RecipeStats`가 함께 생성되고, 검색용 embedding도 생성됩니다.
- 승인에 필요한 필수 레시피 필드가 부족하면 `400`을 반환합니다.

**승인 필수 필드**:

`title`, `description`, `ingredients`, `ingredients_raw`, `instructions`,
`servings`, `cooking_time`, `difficulty`, `category`

**요청 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `title` | string \| null | 레시피 제목 |
| `content` | string \| null | 자유 형식 레시피 본문 |
| `description` | string \| null | 한 줄 설명 |
| `ingredients` | IngredientItem[] \| null | 재료 목록 |
| `ingredients_raw` | string \| null | 재료 원문 텍스트 |
| `instructions` | string[] \| null | 조리 순서 |
| `servings` | float \| null | 인분 수 |
| `cooking_time` | int \| null | 조리 시간(분) |
| `calories` | int \| null | 칼로리(kcal) |
| `difficulty` | string \| null | 난이도 (`easy` / `normal` / `hard`) |
| `category` | string[] \| null | 카테고리 |
| `tags` | string[] \| null | 태그 |
| `tips` | string[] \| null | 조리 팁 |
| `video_url` | string \| null | YouTube 영상 URL |
| `image_url` | string \| null | 이미지 URL |
| `status` | string \| null | 상태 (`PENDING` / `APPROVED` / `REJECTED`) |
| `admin_note` | string \| null | 관리자 검수 메모 |
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
