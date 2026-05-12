# 00. Database Schema

기준 DDL은 [db/schema.sql](../../../db/schema.sql)입니다.

## Core Tables

- `users`
- `user_profiles`
- `recipes`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_image_generations`
- `recipe_stats`
- `pending_recipes`
- `chat_rooms`
- `chat_messages`
- `likes`
- `scraps`

## Ingestion Tables

- `recipe_sources`

`recipe_sources`는 외부 데이터를 수집한 staging 테이블입니다. 수집 원본, 정규화 payload, 검증 상태, import 결과를 보관합니다.

## Image Generation Tables

`recipe_image_generations`는 AI 이미지 생성/재생성 후보와 선택 이력을 저장합니다. 최종 서비스 대표 이미지는 `recipes.image_url`에 저장하고, 생성 후보의 프롬프트, 모델, S3 URL, 실패 사유는 이 테이블에 남깁니다.

## Pending Recipe Enrichment

사용자 제출 레시피의 AI 보정 후보는 초기 구현에서 DB에 저장하지 않습니다. `POST /api/v1/admin/pending-recipes/{id}/enrich`가 `suggested_patch`를 반환하고, 관리자가 확인한 값만 기존 `PATCH` API로 `pending_recipes`에 저장합니다.

## Vector Search

`recipes.embedding`은 `VECTOR(1536)`입니다. pgvector cosine distance 검색에 사용합니다.

## Rebuild Assumption

현재 데이터가 많지 않으므로 초기 단계에서는 migration보다 `db/schema.sql` 기준 재생성을 허용합니다. 운영 데이터가 쌓이기 시작하면 Alembic migration으로 전환합니다.
