from app.api.v1.openapi.errors import VALIDATION_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import (
    USER_RECIPE_EXAMPLE,
    USER_RECIPE_LIST_ITEM_EXAMPLE,
    USER_RECIPE_PUBLIC_EXAMPLE,
    USER_RECIPE_PUBLIC_LIST_RESPONSE_EXAMPLE,
)

USER_RECIPE_NOT_FOUND_RESPONSE = error_response(
    "제출 레시피를 찾을 수 없습니다.",
    "USER_RECIPE_NOT_FOUND",
    "제출 레시피를 찾을 수 없습니다.",
)

USER_NOT_FOUND_RESPONSE = error_response(
    "사용자를 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "사용자를 찾을 수 없습니다.",
)

GET_APPROVED_USER_RECIPES_SUMMARY = "승인된 사용자 레시피 목록 조회"
GET_APPROVED_USER_RECIPES_DESCRIPTION = r"""
승인된 사용자 제출 레시피 목록을 반환합니다.

- `APPROVED` 상태이면서 활성 상태인 사용자 제출 레시피만 반환합니다.
- 로그인하지 않아도 조회할 수 있습니다.
- 최신순(`created_at DESC, user_recipe_id DESC`)으로 반환합니다.
- `cursor`는 이전 응답의 `next_cursor`를 그대로 전달하는 base64url JSON cursor입니다.
- 첫 페이지는 `cursor`를 비워서 요청합니다.
- `limit` 기본값은 20, 최대값은 100입니다.
- 작성자 표시용 `user` 객체(`user_id`, `nickname`)를 포함합니다.
- 목록 응답은 카드 렌더링용으로 `ingredients`, `steps`, `labels`, `nutrition`을 제외하고 `category`, `tags`를 포함합니다.
"""

GET_APPROVED_USER_RECIPES_RESPONSES = {
    200: {
        "description": "승인된 사용자 레시피 목록",
        "content": {
            "application/json": {"example": USER_RECIPE_PUBLIC_LIST_RESPONSE_EXAMPLE}
        },
    },
    400: error_response("잘못된 커서", "INVALID_CURSOR", "Cursor is invalid."),
}

GET_APPROVED_USER_RECIPE_SUMMARY = "승인된 사용자 레시피 단건 조회"
GET_APPROVED_USER_RECIPE_DESCRIPTION = r"""
승인된 사용자 제출 레시피 하나를 조회합니다.

`APPROVED` 상태이면서 활성 상태인 레시피만 조회할 수 있습니다.
로그인하지 않아도 조회할 수 있습니다.
작성자 표시용 `user` 객체(`user_id`, `nickname`)를 포함합니다.
"""

GET_APPROVED_USER_RECIPE_RESPONSES = {
    200: {
        "description": "승인된 사용자 레시피 상세",
        "content": {"application/json": {"example": USER_RECIPE_PUBLIC_EXAMPLE}},
    },
    404: USER_RECIPE_NOT_FOUND_RESPONSE,
}

GET_USER_RECIPES_SUMMARY = "내 제출 레시피 목록 조회"
GET_USER_RECIPES_DESCRIPTION = r"""
현재 사용자가 제출한 레시피 목록을 반환합니다.

- 최신순(`created_at` 내림차순)으로 반환합니다.
- 제출 레시피는 정식 `recipes`에 바로 들어가지 않고 관리자 검수를 기다립니다.
- 사용자가 삭제하면 실제 삭제 대신 `is_active = false`로 변경합니다.
- 목록 응답은 카드 렌더링용으로 `ingredients`, `steps`, `labels`, `nutrition`을 제외하고 `category`, `tags`를 포함합니다.
"""

GET_USER_RECIPES_RESPONSES = {
    200: {
        "description": "제출 레시피 목록",
        "content": {"application/json": {"example": [USER_RECIPE_LIST_ITEM_EXAMPLE]}},
    },
}

GET_USER_RECIPE_SUMMARY = "내 제출 레시피 단건 조회"
GET_USER_RECIPE_DESCRIPTION = r"""
제출한 레시피 하나를 조회합니다.

본인이 제출한 레시피만 조회할 수 있습니다.
"""

GET_USER_RECIPE_RESPONSES = {
    200: {
        "description": "제출 레시피 상세",
        "content": {"application/json": {"example": USER_RECIPE_EXAMPLE}},
    },
    404: USER_RECIPE_NOT_FOUND_RESPONSE,
}

POST_USER_RECIPE_SUMMARY = "레시피 제출"
POST_USER_RECIPE_DESCRIPTION = r"""
사용자가 작성한 레시피를 제출합니다.

제출 레시피는 `PENDING` 상태로 저장되고 관리자가 검수 후 승인하거나 거절합니다.

요청은 `multipart/form-data`입니다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `payload` | stringified JSON | ✓ | 구조화된 레시피 본문 |
| `main_image` | file (`UploadFile`) |  | 대표 이미지 바이너리 |
| `step_images` | file[] (`UploadFile[]`) |  | 단계별 이미지 바이너리. 파일명 stem이 `payload.steps[].client_image_key`와 같아야 합니다. |

이미지 파일 규칙:

- 클라이언트는 이미지를 URL이 아니라 `multipart/form-data`의 파일 파트로 전송합니다.
- 서버는 FastAPI `UploadFile`로 파일을 받습니다.
- 허용 MIME 타입은 `image/jpeg`, `image/png`, `image/webp`입니다.
- 파일당 최대 크기는 10MB입니다.
- 예: `step_images`에 `step-1.png`를 보내면 `payload.steps[].client_image_key`는 `"step-1"`이어야 합니다.
- `client_image_key`가 있는데 매칭 파일이 없거나, 파일은 있는데 매칭 step이 없으면 422를 반환합니다.

`payload` 예시:

```json
{
  "title": "엄마 김치찌개",
  "description": "묵은지를 볶아 깊은 맛을 낸 김치찌개입니다.",
  "servings": 2,
  "cooking_time_minutes": 25,
  "kcal_per_serving": null,
  "difficulty": "easy",
  "source_url": null,
  "category": ["찌개"],
  "tags": ["한식", "얼큰함"],
  "tips": ["묵은지를 쓰면 깊은 맛이 납니다."],
  "warnings": [],
  "ingredients": [
    {
      "group_name": "메인",
      "name": "묵은지",
      "amount_text": "300g",
      "quantity": 300,
      "unit": "g",
      "raw_text": "묵은지 300g"
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "instruction": "묵은지를 충분히 볶습니다.",
      "client_image_key": "step-1"
    }
  ]
}
```

대표 이미지는 `user_recipes.main_image_url`에, 단계 이미지는
`user_recipe_steps.image_url`에 스토리지 object key로 저장하고, API 응답에서 공개 URL로 변환합니다.
"""

POST_USER_RECIPE_RESPONSES = {
    201: {
        "description": "제출 성공",
        "content": {"application/json": {"example": USER_RECIPE_EXAMPLE}},
    },
    404: USER_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

DELETE_USER_RECIPE_SUMMARY = "제출 레시피 삭제"
DELETE_USER_RECIPE_DESCRIPTION = r"""
제출한 레시피를 삭제합니다.

현재 구현은 물리 삭제가 아니라 `is_active = false`로 변경합니다.
본인이 제출한 레시피만 삭제할 수 있습니다.
"""

DELETE_USER_RECIPE_RESPONSES = {
    200: {
        "description": "삭제 성공",
        "content": {
            "application/json": {"example": {"message": "레시피가 삭제되었습니다."}}
        },
    },
    404: USER_RECIPE_NOT_FOUND_RESPONSE,
}
