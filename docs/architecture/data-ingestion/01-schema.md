# 01. Data Ingestion Schema

기준 DDL은 [db/schema.sql](../../../../db/schema.sql)입니다.

## recipe_sources

외부 입력의 staging 테이블입니다.

주요 컬럼:

- `source_type`: `INTERNAL`, `USER_SUBMISSION`, `WEB_SCRAPE`, `VIDEO`, `EXTERNAL_API`
- `source_site`: `10000recipe`, `youtube`, `admin`, `user` 등
- `parser_type`: `MANUAL`, `HTML`, `AI`, `API`
- `source_recipe_id`
- `source_url`
- `source_author_name`
- `source_author_url`
- `raw_payload`
- `normalized_payload`
- `source_metadata`
- `normalized_metadata`
- `content_hash`
- `status`
- `validation_errors`
- `imported_recipe_id`

## recipes

서비스에서 사용하는 정식 레시피 테이블입니다. 기존 API 호환을 위해 `ingredients`, `instructions`, `category`, `tags`, `tips` JSONB 필드를 유지합니다.

추가 강화 필드:

- 출처: `source_id`, `source_type`, `source_site`, `source_recipe_id`, `source_url`
- 파싱 방식: `parser_type`
- 작성자 출처: `source_author_name`, `source_author_url`
- 이미지: `image_url`, `thumbnail_url`, `image_urls`
- 추천 메타: `cuisine_type`, `dish_type`, `cooking_method`, `main_ingredients`, `taste_keywords`
- 메타 JSON: `source_metadata`, `normalized_metadata`

## recipe_ingredients

재료를 행 단위로 저장합니다. 재료 검색, 제외 조건, 재료 그룹 표시, 냉장고 재료 매칭을 위해 사용합니다.

## recipe_steps

조리 단계를 행 단위로 저장합니다. 단계별 이미지, YouTube timestamp, 조리 단계 품질 검수에 사용합니다.

## recipe_stats

좋아요/스크랩 count를 저장합니다. `recipes` insert 시 자동 생성되고, `likes`, `scraps` 변경 시 trigger로 갱신됩니다.
