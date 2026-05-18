# 01. User API

User API는 일반 사용자 앱에서 호출하는 public contract다. scraping, source import, AI image generation, embedding backfill 같은 운영 작업은 포함하지 않는다.

## Users

```text
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users/me/profile
POST   /api/v1/users/me/profile
DELETE /api/v1/users/me/profile
GET    /api/v1/users/me/scraps
```

역할:

- 내 계정 정보 조회/수정
- 추천 개인화를 위한 프로필 조회/수정
- 내가 스크랩한 레시피 목록 조회

현재 인증 연동 전까지는 임시 사용자 컨텍스트를 사용하지만, API contract는 인증된 사용자 기준으로 설계한다.

## Profile User Input

`user_profiles.user_input`은 사용자가 직접 입력한 취향, 알레르기, 조리 조건 문장 배열이다.

저장 순서:

- DB에는 오래된 입력부터 저장한다.
- `POST /me/profile`은 입력 문장을 agent가 사용자 정보인지 확인하고, 저장용 한 문장으로 정리한 뒤 배열 마지막에 append한다.
- `GET /me/profile` 응답은 최신 입력을 먼저 볼 수 있도록 마지막 요소부터 반환한다.

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

삭제 API는 요청한 문장과 정확히 일치하는 항목을 제거한다. 응답은 항상 최신순 `user_input` 배열이다.

채팅 중 agent가 명확한 사용자 정보를 발견하면 정책에 따라 profile update 후보를 만들 수 있다. 민감하거나 모호한 정보는 바로 저장하지 않고 확인 흐름을 거친다.

## Recipes

```text
GET    /api/v1/recipes
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

Detail response는 화면에 필요한 값을 한 번에 제공한다.

- 기본 레시피 정보 (`title`, `description`, `summary`, `servings`, `cooking_time_minutes`, `kcal_per_serving`, `difficulty`)
- 재료 (`ingredients`: IngredientItem 목록)
- 조리 단계 (`steps`: RecipeStepResponse 목록 — `step_no`, `title`, `instruction`, `tip` 포함)
- 카테고리/태그/팁 (`category`, `tags`, `tips`)
- 미디어 (`video_url`, `image_url`)
- 좋아요/스크랩 상태
- 통계
- 출처 표시 정보 (SOURCE 타입 레시피의 경우 `source_id`로 `recipe_sources` JOIN)

이미지는 `recipes` 본문 컬럼이 아니라 `recipe_media`에서 `MAIN`, `THUMBNAIL` 역할을 조회해 응답한다.

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

## Pending Recipes

```text
GET    /api/v1/pending-recipes
GET    /api/v1/pending-recipes/{pending_recipe_id}
POST   /api/v1/pending-recipes
DELETE /api/v1/pending-recipes/{pending_recipe_id}
```

사용자가 직접 제출한 레시피는 바로 `recipes`에 들어가지 않고 `pending_recipes`에 저장한다. 요청 본문은 `title`(필수)과 `submission_text`(필수)를 받는다. 검수 대상 구조화 값인 `draft_payload`와 AI 보정 후보인 `ai_suggested_patch`는 빈 기본 구조로 초기화한다. 사용자가 삭제하면 실제 삭제 대신 `is_active = false`로 바꾸어 관리자 검수 상태(`PENDING`, `APPROVED`, `REJECTED`)와 분리한다.

## Excluded From User API

- scraping trigger
- recipe source import
- AI image generation
- embedding backfill
- source approval/retry action
- system retry action
