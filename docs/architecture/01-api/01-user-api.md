# 01. User API

User API는 일반 사용자 앱에서 호출하는 public contract다. scraping, source import, AI image generation, embedding backfill 같은 운영 작업은 포함하지 않는다.

## Guest Chat

```text
POST   /api/v1/guest/chat
```

비로그인 사용자도 사용할 수 있는 채팅 엔드포인트다. 채팅 방을 만들지 않고 요청 본문에 대화 히스토리를 직접 포함한다. 응답은 SSE 스트림으로 반환한다.

인증이 없으므로 사용자 프로필 기반 개인화, 채팅 히스토리 저장, 좋아요/스크랩은 사용할 수 없다.

## Users

```text
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users/me/profile
POST   /api/v1/users/me/profile
DELETE /api/v1/users/me/profile
```

역할:

- 내 계정 정보 조회/수정
- 추천 개인화를 위한 프로필 조회/수정

현재 인증 연동 전까지는 임시 사용자 컨텍스트를 사용하지만, API contract는 인증된 사용자 기준으로 설계한다.

## Profile User Input

`user_profiles.user_input`은 사용자가 직접 입력한 취향, 알레르기, 조리 조건 문장 배열이다.

저장 순서:

- DB에는 오래된 입력부터 저장한다.
- `POST /me/profile`은 한두 문장의 입력만 받는다.
- 입력 문장을 agent가 사용자 정보인지 확인하고, 저장용 한 문장으로 정리한 뒤 배열 마지막에 append한다.

추가:

```http
POST /api/v1/users/me/profile
```

```json
{
  "text": "새우 알레르기가 있어요"
}
```

POST 저장 조건:

- 장기적으로 쓸 수 있는 본인 정보여야 한다.
- 취향, 알레르기, 식이 제한, 조리 실력, 선호 조리 시간, 보통 인분 수 같은 개인화 정보만 저장한다.
- "오늘은 닭고기 빼줘"처럼 임시 요청이면 저장하지 않는다.
- 타인 정보, 질문, 농담, 단순 레시피 요청이면 저장하지 않는다.
- 저장될 문장은 agent가 한 문장으로 정리한다.

삭제:

```http
DELETE /api/v1/users/me/profile
```

```json
{
  "user_input": ["새우 알레르기가 있어요", "매운 음식은 피하고 싶어요"]
}
```

삭제 API는 요청한 문장과 정확히 일치하는 항목을 제거한다.

채팅 중 agent가 명확한 사용자 정보를 발견하면 정책에 따라 profile update 후보를 만들 수 있다. 민감하거나 모호한 정보는 바로 저장하지 않고 확인 흐름을 거친다.

## Recipes

```text
GET    /api/v1/recipes
GET    /api/v1/recipes/scraps
GET    /api/v1/recipes/{recipe_id}
POST   /api/v1/recipes/{recipe_id}/likes
DELETE /api/v1/recipes/{recipe_id}/likes
POST   /api/v1/recipes/{recipe_id}/scraps
DELETE /api/v1/recipes/{recipe_id}/scraps
```

List query:

- `cursor`
- `limit`
- `sort=latest|likes|scraps`

`GET /api/v1/recipes/scraps`는 현재 사용자가 스크랩한 레시피만 반환한다.
정렬은 스크랩한 최신순이며 커서는 `created_at DESC, scrap_id DESC` 순서를 기준으로 한다.

Detail response는 화면에 필요한 값을 한 번에 제공한다.

- 기본 레시피 정보 (`title`, `description`, `summary`, `servings`, `cooking_time_minutes`, `kcal_per_serving`, `difficulty`)
- 재료 (`ingredients`: `group_name`, `name`, `amount_text`, `quantity`, `unit`, `note`, `raw_text`, `is_optional`)
- 조리 단계 (`steps`: RecipeStepResponse 목록 — `step_no`, `instruction`, `image_url`, `tip` 포함)
- 카테고리/태그/팁 (`category`, `tags`, `tips`)
- 원본 대표 이미지 (`main_image_url`)
- 좋아요/스크랩 상태
- 통계
- 출처 표시 정보 (`source_url`, SOURCE 타입 레시피의 상세 provenance는 `source_id`로 `recipe_sources` JOIN)

목록 응답은 카드 렌더링용으로 `description`, `ingredients`, `steps`, `tips`, `source_url`을 제외하고 `category`, `tags`, `main_image_url`을 포함한다.

## Chat

```text
GET    /api/v1/chat/rooms
POST   /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
POST   /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}
```

Chat API는 추천 또는 일반 답변을 반환한다.

응답에 포함될 수 있는 정보:

- assistant message
- 추천 레시피 id 목록
- 추천 근거 요약
- 사용자 검색 조건
- 프로필 업데이트 후보 또는 확인 정보
- live research 사용 여부

## User Recipes

```text
GET    /api/v1/user-recipes?cursor=...&limit=20
GET    /api/v1/user-recipes/{user_recipe_id}
POST   /api/v1/user-recipes/{user_recipe_id}/reports
GET    /api/v1/user-recipes/me
GET    /api/v1/user-recipes/me/{user_recipe_id}
POST   /api/v1/user-recipes/me
DELETE /api/v1/user-recipes/me/{user_recipe_id}
```

`/api/v1/user-recipes`는 승인된 사용자 제출 레시피의 공개 조회 API다.
`status = APPROVED`, `is_active = true`인 레시피만 반환한다.
작성자 표시를 위해 `user` 객체를 포함하며, 공개 필드는 `user_id`, `nickname`으로 제한한다.

```text
GET    /api/v1/user-recipes?cursor=...&limit=20
GET    /api/v1/user-recipes/{user_recipe_id}
POST   /api/v1/user-recipes/{user_recipe_id}/reports
```

목록 응답은 cursor pagination 래퍼를 사용한다.

```json
{
  "items": [],
  "next_cursor": null,
  "has_next": false
}
```

`POST /api/v1/user-recipes/{user_recipe_id}/reports`는 공개된 사용자 제출 레시피를 신고한다.
`APPROVED`, `is_active = true`인 레시피만 신고할 수 있고, 본인 레시피와 중복 신고는 거절한다.
신고는 레시피를 즉시 비노출하지 않고 관리자 검토 큐에 저장한다.

`/api/v1/user-recipes/me`는 현재 사용자가 직접 제출한 레시피 관리 API다.
사용자가 직접 제출한 레시피는 바로 `recipes`에 들어가지 않고 `user_recipes`와
`user_recipe_*` 하위 테이블에 검수 가능한 구조화 초안으로 저장한다. 생성 요청은
이미지 업로드를 함께 받을 수 있도록 `multipart/form-data`를 사용한다. 사용자가
삭제하면 실제 삭제 대신 `is_active = false`로 바꾸어 관리자 검수 상태(`PENDING`,
`APPROVED`, `REJECTED`)와 분리한다.

```http
POST /api/v1/user-recipes/me
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `payload` | stringified JSON | 필수 | 구조화된 레시피 초안 |
| `main_image` | file | 선택 | 대표 이미지 |
| `step_images` | file[] | 선택 | 단계 이미지. 파일명 stem이 `payload.steps[].client_image_key`와 일치해야 한다. |

`payload` 필수값:

- `title`
- `description`
- `servings`
- `cooking_time_minutes`
- `difficulty`
- `ingredients`
- `steps`

`payload` 예시:

```json
{
  "title": "엄마표 김치찌개",
  "description": "묵은지를 충분히 볶아서 깊은 맛을 내는 김치찌개입니다.",
  "servings": 2,
  "cooking_time_minutes": 30,
  "kcal_per_serving": null,
  "difficulty": "easy",
  "source_url": null,
  "ingredients": [
    {
      "group_name": "메인",
      "name": "묵은지",
      "amount_text": "300g",
      "quantity": 300,
      "unit": "g",
      "note": "충분히 익은 것",
      "raw_text": "묵은지 300g",
      "is_optional": false,
      "sort_order": 1
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "instruction": "돼지고기를 볶습니다.",
      "tip": null,
      "client_image_key": "step-1",
      "sort_order": 1
    }
  ],
  "labels": [
    {
      "label_type": "CATEGORY",
      "label_value": "찌개",
      "sort_order": 1
    }
  ]
}
```

이미지 검증:

- 허용 타입은 `image/jpeg`, `image/png`, `image/webp`다.
- 파일당 최대 크기는 10MB다.
- `client_image_key`가 있으면 같은 stem의 `step_images` 파일이 반드시 있어야 한다.
- 어떤 step에도 매칭되지 않는 `step_images` 파일은 422로 거절한다.
- 사용자 생성 API에서는 이미지 URL을 직접 받지 않는다. 서버가 S3에 업로드한 URL을 `user_recipes.main_image_url`, `user_recipe_steps.image_url`에 저장한다.

개발 환경은 `docker-compose.dev.yml`의 MinIO를 로컬 S3로 사용한다. 기본 URL은 `http://localhost:9000`, 콘솔은 `http://localhost:9001`이다.

## Excluded From User API

- scraping trigger
- recipe source import
- AI image generation
- embedding backfill
- source approval/retry action
- system retry action
