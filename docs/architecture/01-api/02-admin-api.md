# 02. Admin API

Admin API는 관리자 화면에서 사용하는 내부용 API다.

## Current Scope

### Recipe Sources

```text
GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/import
```

`recipe_sources` 목록 조회, 승인/거절, import 트리거를 제공한다. 실제 파싱 결과 상세는 `recipe_source_extractions*` staging 테이블에 있다.

### Recipes

```text
GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}
```

관리자용 레시피 목록/상세 조회다. 일반 사용자 응답과 달리 재료, 조리 단계, 라벨, 영양 정보, 이미지 목록, 분류 정보를 모두 포함한다. 이미지는 `recipes` 본문 컬럼이 아니라 `recipe_media`에서 조회한다.

source 원본 정보(URL, 작성자, 라이선스)는 `recipes.source_id`로 `recipe_sources`를 JOIN해서 반환한다.

### Chat Rooms

```text
DELETE /api/v1/admin/chat-rooms/{room_id}
```

Hard deletes a chat room and its messages from the database. User-facing
`DELETE /api/v1/chat/rooms/{room_id}` remains a soft delete.

### User Recipes

```text
GET    /api/v1/admin/user-recipes
GET    /api/v1/admin/user-recipes/{pending_recipe_id}
PATCH  /api/v1/admin/user-recipes/{pending_recipe_id}
DELETE /api/v1/admin/user-recipes/{pending_recipe_id}
```

사용자가 제출한 레시피 검수 및 승인 처리다. `APPROVED` 처리 시 제출 레시피가 서비스에 노출 가능한 상태가 된다. `recipes*` production 테이블 import는 별도 작업으로 처리한다.

사용자 삭제 또는 탈퇴 흐름으로 `is_active = false`가 된 제출 레시피만 관리자 API에서 물리 삭제할 수 있다. 활성 제출건은 관리자 화면에서 바로 삭제하지 않고 검수 상태만 변경한다.

## Deferred

### Activate / Deactivate

```text
POST   /api/v1/admin/recipes/{recipe_id}/activate
POST   /api/v1/admin/recipes/{recipe_id}/deactivate
POST   /api/v1/admin/recipes/{recipe_id}/refresh-embedding
```

레시피 노출 상태 변경과 embedding 재생성은 예정 API다.

### AI Image Generations

```text
GET    /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

AI 이미지 생성 결과는 `recipe_image_generations`와 `recipe_media(image_role = GENERATED_CANDIDATE)`에 보관한다. 관리자가 선택한 후보가 `MAIN` 또는 `THUMBNAIL`로 지정된다.

### Pending Recipe AI Enrichment

```text
POST /api/v1/admin/user-recipes/{pending_recipe_id}/enrich
```

정책:

- AI 보정 patch는 기본적으로 `draft_payload`에 바로 덮어쓰지 않는다.
- 응답 또는 저장 후보는 `ai_suggested_patch`로 관리한다.
- 관리자가 확인한 값만 `PATCH /api/v1/admin/user-recipes/{pending_recipe_id}`로 `draft_payload`에 반영한다.

### Scraper Operations

현재는 `scraper_runs` 테이블 없이 CLI 스크립트와 `recipe_sources` 상태로 관리한다. 관리 화면에서 run 추적이 필요해지면 아래 API와 테이블을 추가한다.

```text
GET    /api/v1/admin/scraper-runs
GET    /api/v1/admin/scraper-runs/{run_id}
POST   /api/v1/admin/scraper-runs
POST   /api/v1/admin/scraper-runs/{run_id}/cancel
```

## Admin Permissions

Admin API는 `ADMIN` 권한이 필요하다. 실제 인증은 인증 연동 시 API contract를 role 기반 권한으로 제한한다.
