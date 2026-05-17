# 00. Database Schema

기준 DDL은 [db/schema.sql](../../../db/schema.sql)이다. 현재는 초기 개발 단계라 rebuildable schema를 우선 사용하고, 운영 데이터가 쌓이기 시작하면 Alembic migration으로 전환한다.

## Core Tables

- `users`
- `user_profiles`
- `recipes`
- `recipe_nutrition`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_labels`
- `recipe_classifications`
- `recipe_media`
- `recipe_image_generations`
- `recipe_embeddings`
- `recipe_quality_scores`
- `recipe_stats`
- `pending_recipes`
- `chat_rooms`
- `chat_messages`
- `likes`
- `scraps`

## Ingestion Tables

- `recipe_sources`
- `recipe_source_extractions`
- `recipe_source_quality_scores`
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
- 영양 정보: `recipe_nutrition`
- 추천/검색 분류: `recipe_classifications`
- 추천/검색 분류 작업 상태: `recipes.classification_status`, `recipes.classified_at`
- 반복 label: `recipe_labels`
- 이미지/영상: `recipe_media`
- 이미지 생성 이력: `recipe_image_generations`
- 벡터 검색: `recipe_embeddings`

JSONB는 원본 백업이나 구조가 자주 바뀌는 보조 metadata에 제한적으로 사용한다.

## Source Compatibility

foodsafetykorea와 만개의레시피는 같은 staging model을 사용한다.

- foodsafetykorea 중복 기준: `source_dataset_id + source_record_id`
- 웹 source 중복 기준: `source_site + source_recipe_id`, `source_url`, `raw_content_hash`
- 공공데이터 영양 정보는 extraction nutrition 컬럼을 거쳐 `recipe_nutrition`으로 이동한다.
- production recipe는 `source_id` FK로 원본 source를 추적한다.

## recipes ↔ recipe_sources 관계

`recipes.source_id`는 `recipe_sources`를 가리키는 FK이며 `ON DELETE RESTRICT`다. recipe가 존재하는 source는 DB 레벨에서 삭제가 차단된다.

source URL, 작성자, 라이선스 등 원본 정보는 `recipes`에 복사하지 않는다. 필요한 경우 `source_id`로 JOIN해 `recipe_sources`에서 직접 읽는다.

## Image Generation Tables

`recipe_image_generations`는 AI 이미지 생성 요청과 결과 상태를 저장한다. 실제 이미지 URL과 storage metadata는 `recipe_media`에 저장한다.

원본 source 이미지 URL은 staging에만 보관한다. production import 단계에서 원본 이미지 URL을 `recipe_media`로 바로 복사하지 않는다. 서비스 노출 이미지는 생성/업로드/선택 과정을 거쳐 `recipe_media.image_role = MAIN` 또는 `THUMBNAIL`이 된 media를 사용한다.

## Pending Recipes

`pending_recipes`는 사용자가 제출한 레시피를 바로 `recipes`에 넣지 않고 검수 가능한 draft로 보관하는 테이블이다.

- `submission_text`: 사용자가 처음 제출한 원문 설명
- `draft_payload`: 관리자 검수 대상 구조화 draft 값
- `ai_suggested_patch`: AI 보정 후보
- `validation_errors`: 승인 전 보완이 필요한 필드나 검증 오류
- `status`: `PENDING`, `APPROVED`, `REJECTED`
- `is_active`: 사용자 삭제 여부를 표현하는 soft delete flag
- `import_status`: `NOT_IMPORTED`, `IMPORTED`, `FAILED`
- `reviewed_by`, `reviewed_at`: 관리자 검수 이력
- `imported_recipe_id`, `imported_at`: 별도 import 작업으로 생성된 production recipe 추적

AI 보정 결과는 기본적으로 `draft_payload`에 바로 덮어쓰지 않는다. 관리자가 확인한 값만 admin API로 반영하고, `APPROVED` 시 제출 레시피가 서비스에 노출 가능한 상태가 된다. production `recipes*` 테이블 import는 별도 작업으로 처리한다.

관리자 물리 삭제는 `is_active = false`인 제출 레시피에만 허용한다. 활성 제출 레시피의 삭제는 사용자 삭제/탈퇴 흐름에서 soft delete로 먼저 처리한다.

## Vector Search

embedding은 `recipe_embeddings.embedding`에 저장한다. recipe 본문 테이블과 분리해 검색 목적별 embedding을 여러 개 둘 수 있게 한다.

## Rebuild Assumption

현재는 `db/schema.sql` 기준 재생성을 허용한다. 운영 데이터가 의미 있게 쌓이면 migration-first 운영으로 전환한다.
