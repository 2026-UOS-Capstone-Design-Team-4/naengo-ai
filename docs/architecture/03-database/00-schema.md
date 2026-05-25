# 00. Database Schema

기준 DDL은 [db/schema.sql](../../../db/schema.sql)이다. 현재는 초기 개발 단계라 rebuildable schema를 우선 사용하고, 운영 데이터가 쌓이기 시작하면 Alembic migration으로 전환한다.

## Core Tables

- `users`
- `user_identities`
- `user_profiles`
- `recipes`
- `recipe_nutrition`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_labels`
- `recipe_classifications`
- `recipe_embeddings`
- `recipe_quality_scores`
- `recipe_stats`
- `user_recipes`
- `user_recipe_ingredients`
- `user_recipe_steps`
- `user_recipe_labels`
- `user_recipe_nutrition`
- `user_recipe_reports`
- `chat_rooms`
- `chat_messages`
- `likes`
- `scraps`


## Ingestion Tables

- `recipe_sources`
- `recipe_source_extractions`
- `recipe_source_quality_scores`
- `recipe_source_extracted_nutrition`
- `recipe_source_extracted_ingredients`
- `recipe_source_extracted_steps`
- `recipe_source_extracted_labels`

`recipe_sources`는 raw payload와 source lifecycle 상태를 저장한다. 파싱된 staging 값은 `recipe_source_extractions*`에 저장하고, staging 품질은 `recipe_source_quality_scores`에 저장한다. 승인된 source만 production recipe tables로 import한다.

## Why No `normalized_payload`

`normalized_payload` 또는 `normalized_metadata` 같은 큰 JSONB 컬럼은 책임 경계가 흐려지기 쉬워 사용하지 않는다. 현재 설계는 용도별 테이블을 명확히 나눈다.

- 원본 백업: `recipe_sources.raw_payload`
- staging 본문: `recipe_source_extractions*`
- staging 품질: `recipe_source_quality_scores`
- 서비스 데이터: `recipes*`
- 식사 인분: `recipes.servings`, `recipe_source_extractions.servings`
- 완성 분량: `recipes.yield_quantity`, `recipes.yield_unit`,
  `recipe_source_extractions.yield_quantity`, `recipe_source_extractions.yield_unit`
- 영양 정보: `recipe_nutrition`, `recipe_source_extracted_nutrition`
- 추천/검색 분류: `recipe_classifications`
- 추천/검색 분류 작업 상태: `recipes.classification_status`, `recipes.classified_at`
- 반복 label: `recipe_labels`
- 이미지 URL: `recipes.source_main_image_url`, `recipe_steps.image_url`
- 벡터 검색: `recipe_embeddings`

JSONB는 원본 백업이나 구조가 자주 바뀌는 보조 metadata에 제한적으로 사용한다.

## Source Compatibility

외부 source는 같은 staging model을 사용한다.

- 웹 source 중복 기준: `source_site + source_recipe_id`, `source_url`, `raw_content_hash`
- 상세 영양 정보는 `recipe_source_extracted_nutrition`을 거쳐 `recipe_nutrition`으로 이동한다.
- production recipe는 `source_id` FK로 원본 source를 추적한다.

## recipes ↔ recipe_sources 관계

`recipes.source_id`는 `recipe_sources`를 가리키는 FK이며 `ON DELETE RESTRICT`다. recipe가 존재하는 source는 DB 레벨에서 삭제가 차단된다.

원본 URL과 원본 대표 이미지 URL은 조회 편의를 위해 `recipes.source_url`,
`recipes.source_main_image_url`에도 복사한다. 작성자, 라이선스 등 상세 원본 정보는
필요한 경우 `source_id`로 JOIN해 `recipe_sources`에서 직접 읽는다.

## User Identity

`user_identities`는 OAuth provider(KAKAO, GOOGLE, NAVER, APPLE)별 로그인 식별자를 저장한다. 한 사용자가 여러 provider로 연결될 수 있다. `users` 1:N 관계이며, `provider + provider_user_id`가 unique constraint다.

## Image URL Policy

별도 media 테이블은 사용하지 않는다. 이미지 URL은 각 테이블의 컬럼으로 관리한다.

- `recipes.source_main_image_url`: 레시피 대표 이미지 URL
- `recipe_steps.image_url`: 조리 단계 이미지 URL
- `recipe_source_extractions.source_main_image_url`, `source_thumbnail_url`: staging 원본 이미지 URL
- `recipe_source_extracted_steps.source_image_url`: staging 단계 이미지 URL

## User Recipes

`user_recipes`는 사용자가 제출한 레시피를 바로 `recipes`에 넣지 않고 검수 가능한 draft로 보관하는 테이블이다.

- `title`, `description`, `servings`, `cooking_time_minutes`, `difficulty`: 관리자 검수 대상 구조화 본문 값
- `user_recipe_ingredients`, `user_recipe_steps`, `user_recipe_labels`, `user_recipe_nutrition`: 사용자 제출 레시피의 구조화 반복 데이터
- `status`: `PENDING`, `APPROVED`, `REJECTED`
- `is_active`: 사용자 삭제 여부를 표현하는 soft delete flag
- `import_status`: `NOT_IMPORTED`, `IMPORTED`, `FAILED`
- `reviewed_by`, `reviewed_at`: 관리자 검수 이력
- `imported_recipe_id`, `imported_at`: 별도 import 작업으로 생성된 production recipe 추적

AI 보정 결과는 별도 JSON draft 컬럼에 저장하지 않는다. 관리자가 확인한 값만 admin API로 구조화 필드에 반영하고, `APPROVED` 시 제출 레시피가 서비스에 노출 가능한 상태가 된다. production `recipes*` 테이블 import는 별도 작업으로 처리한다.

관리자 물리 삭제는 `is_active = false`인 제출 레시피에만 허용한다. 활성 제출 레시피의 삭제는 사용자 삭제/탈퇴 흐름에서 soft delete로 먼저 처리한다.

## User Recipe Reports

`user_recipe_reports`는 공개된 사용자 제출 레시피에 대한 사용자 신고를 저장한다.
신고는 레시피 노출 상태와 분리해 관리자 검토 큐로 관리한다.

- `user_recipe_id`: 신고 대상 사용자 레시피
- `reporter_user_id`: 신고한 사용자
- `recipe_owner_user_id`: 신고 대상 레시피 작성자
- `reason`: `INAPPROPRIATE`, `COPYRIGHT`, `SPAM`, `DANGEROUS`, `FALSE_INFO`, `OTHER`
- `status`: `PENDING`, `REVIEWING`, `RESOLVED`, `REJECTED`
- `review_note`, `reviewed_by`, `reviewed_at`: 관리자 검토 결과

같은 사용자는 같은 사용자 레시피를 한 번만 신고할 수 있다.

## Vector Search

embedding은 `recipe_embeddings.embedding`에 저장한다. recipe 본문 테이블과 분리해 검색 목적별 embedding을 여러 개 둘 수 있게 한다.

## Rebuild Assumption

현재는 `db/schema.sql` 기준 재생성을 허용한다. 운영 데이터가 의미 있게 쌓이면 migration-first 운영으로 전환한다.
