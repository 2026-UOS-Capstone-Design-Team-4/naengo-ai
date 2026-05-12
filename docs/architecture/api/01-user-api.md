# 01. User API

User API는 일반 사용자 앱에서 호출하는 안정적인 public contract입니다. 관리자 검수, import, AI 이미지 생성 같은 운영 액션은 포함하지 않습니다.

## Users

```text
GET   /api/v1/users/me
PATCH /api/v1/users/me
GET   /api/v1/users/me/profile
PATCH /api/v1/users/me/profile
GET   /api/v1/users/me/scraps
```

역할:

- 내 계정 정보 조회/수정
- 추천 개인화를 위한 프로필 조회/수정
- 내가 스크랩한 레시피 목록 조회

로그인 고도화 전까지는 임시 사용자 식별자를 사용할 수 있지만, API contract는 인증된 사용자 기준으로 설계합니다.

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
- `sort=latest|likes|relevance`
- `category`
- `main_ingredient`
- `cooking_time_max`
- `difficulty`

Detail response는 앱 화면에 필요한 값을 한 번에 제공합니다.

- 기본 레시피 정보
- 재료
- 조리 단계
- 대표 이미지/썸네일
- 좋아요/스크랩 상태
- 통계
- 출처 표기 정보

## Chat

```text
GET    /api/v1/chat/rooms
POST   /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
POST   /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}
```

Chat API는 추천형 응답을 반환합니다.

응답에 포함할 수 있는 정보:

- assistant message
- 추천 레시피 id 목록
- 추천 근거 요약
- 사용한 검색 조건
- live research 사용 여부

## Pending Recipes

```text
GET    /api/v1/pending-recipes
GET    /api/v1/pending-recipes/{pending_recipe_id}
POST   /api/v1/pending-recipes
DELETE /api/v1/pending-recipes/{pending_recipe_id}
```

사용자가 직접 제출한 레시피는 바로 `recipes`에 들어가지 않고 `pending_recipes`에 저장합니다. 관리자가 승인해야 정식 레시피가 됩니다.

## Excluded From User API

다음 기능은 User API에 노출하지 않습니다.

- scraping trigger
- recipe source import
- AI image generation
- embedding backfill
- admin review action
- system retry action
