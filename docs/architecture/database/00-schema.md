# 00. Database Schema

기준 DDL은 [db/schema.sql](../../../db/schema.sql)입니다.

## Core Tables

- `users`
- `user_profiles`
- `recipes`
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
- `recipe_source_extracted_ingredients`
- `recipe_source_extracted_steps`
- `recipe_source_extracted_labels`

`recipe_sources`는 raw payload와 lifecycle 상태를 저장합니다. 파싱된 후보값은 `recipe_source_extractions*`에 저장하고, 승인 후 정식 recipe tables로 복사합니다.

## Why No `normalized_payload`

`normalized_payload`와 `normalized_metadata`는 역할이 겹쳐서 경계가 흐려졌습니다. 새 설계에서는 다음처럼 나눕니다.

- 원본 백업: `recipe_sources.raw_payload`
- 검수 후보값: `recipe_source_extractions*`
- 서비스 데이터: `recipes*`
- 추천/검색 분류: `recipe_classifications`
- 반복 라벨: `recipe_labels`
- 이미지/영상: `recipe_media`
- 벡터 검색: `recipe_embeddings`

JSONB는 원본 백업이나 배열형 분류값처럼 구조가 자주 바뀌는 영역에만 제한적으로 사용합니다.

## Image Generation Tables

`recipe_image_generations`는 AI 이미지 생성/재생성 요청과 결과 상태를 저장합니다. 실제 이미지 URL은 `recipe_media`에 저장하고, 선택된 이미지는 `image_role = MAIN` 또는 `image_role = THUMBNAIL`로 표시합니다.

## Pending Recipe Enrichment

사용자 제출 레시피의 AI 보정 후보는 초기 구현에서 DB에 저장하지 않습니다. `POST /api/v1/admin/pending-recipes/{id}/enrich`가 `suggested_patch`를 반환하고, 관리자가 확인한 값만 기존 `PATCH` API로 `pending_recipes`에 저장합니다.

## Vector Search

embedding은 `recipe_embeddings.embedding`에 저장합니다. recipe 본문 테이블에서 embedding을 분리해 검색 목적별 embedding을 여러 개 둘 수 있게 합니다.

## Rebuild Assumption

현재 데이터가 많지 않으므로 초기 단계에서는 migration보다 `db/schema.sql` 기준 재생성을 허용합니다. 운영 데이터가 쌓이기 시작하면 Alembic migration으로 전환합니다.
