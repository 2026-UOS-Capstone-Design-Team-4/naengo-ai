# 01. Data Ingestion Schema

기준 DDL은 [db/schema.sql](../../../../db/schema.sql)입니다.

## Design Change

이전 설계의 `normalized_payload`, `normalized_metadata`는 경계가 흐렸습니다. 새 설계는 다음 원칙을 따릅니다.

- 원본 백업은 `recipe_sources.raw_payload`에만 둡니다.
- 파싱 후보값은 `recipe_source_extractions*` 테이블에 명시 컬럼으로 저장합니다.
- 정식 서비스 데이터는 `recipes*` 테이블에 저장합니다.
- 추천/검색 분류값은 `recipe_classifications`로 분리합니다.
- 이미지/영상은 `recipe_media`로 분리합니다.
- embedding은 `recipe_embeddings`로 분리합니다.

## Source Tables

### `recipe_sources`

외부 입력의 원본과 lifecycle 상태를 저장합니다.

주요 컬럼:

- `source_type`
- `source_site`
- `parser_type`
- `source_recipe_id`
- `source_url`
- `source_author_name`
- `source_author_url`
- `source_published_at`
- `raw_payload`
- `raw_content_hash`
- `collection_status`
- `parse_status`
- `review_status`
- `import_status`
- `validation_errors`
- `parser_version`
- `imported_recipe_id`

### `recipe_source_extractions`

원본에서 추출한 레시피 후보의 본문 정보를 저장합니다.

주요 컬럼:

- `source_id`
- `title`
- `subtitle`
- `summary`
- `description`
- `servings`
- `prep_time_minutes`
- `cook_time_minutes`
- `total_time_minutes`
- `calories`
- `difficulty`
- `difficulty_score`
- `source_main_image_url`
- `source_thumbnail_url`
- `source_video_url`
- `content_hash`
- `completeness_score`
- `confidence_score`

### `recipe_source_extracted_ingredients`

검수 전 재료 후보입니다.

- `group_name`
- `name`
- `normalized_name`
- `amount_text`
- `quantity`
- `unit`
- `note`
- `raw_text`
- `is_optional`
- `sort_order`

### `recipe_source_extracted_steps`

검수 전 조리 단계 후보입니다.

- `step_no`
- `title`
- `instruction`
- `duration_minutes`
- `temperature`
- `equipment`
- `source_image_url`
- `tip`
- `raw_text`
- `sort_order`

### `recipe_source_extracted_labels`

검수 전 태그, 팁, 카테고리, 경고 문구 후보입니다.

- `label_type`: `TAG`, `TIP`, `CATEGORY`, `WARNING`
- `label_value`
- `confidence_score`
- `source`: `SCRAPE`, `RULE`, `AI`, `ADMIN`

## Production Tables

### `recipes`

서비스에 노출하는 정식 레시피의 핵심 본문입니다.

- `title`
- `subtitle`
- `summary`
- `description`
- `servings`
- `prep_time_minutes`
- `cook_time_minutes`
- `total_time_minutes`
- `calories`
- `difficulty`
- `difficulty_score`
- `status`
- `visibility`
- `author_type`
- `source_*`

### `recipe_ingredients`

검색 가능한 재료 단위 테이블입니다. `amount_text`는 사용자가 보는 수량 문자열이고, `quantity`/`unit`은 가능한 경우에만 구조화합니다.

### `recipe_steps`

조리 단계입니다. 단계 이미지는 직접 컬럼에 넣지 않고 `recipe_media.step_id`로 연결합니다.

### `recipe_labels`

태그, 팁, 카테고리, 경고 문구처럼 반복 가능한 라벨을 저장합니다.

### `recipe_classifications`

추천/검색에 쓰는 분류 축입니다.

- `cuisine_type`
- `dish_type`
- `cooking_methods`
- `meal_types`
- `occasions`
- `situations`
- `main_ingredients`
- `taste_keywords`
- `texture_keywords`
- `diet_keywords`
- `allergen_keywords`
- `equipment`
- `season`
- `category_labels`

### `recipe_media`

이미지/영상 저장소입니다.

- `media_type`
- `image_role`
- `source_url`
- `storage_url`
- `thumbnail_url`
- `width`
- `height`
- `mime_type`
- `is_primary`

### `recipe_embeddings`

embedding은 recipe 본문 테이블에서 분리합니다. 검색 목적별로 여러 embedding을 둘 수 있습니다.

### `recipe_quality_scores`

완성도, 이미지 품질, 조리 단계 품질, 분류 신뢰도, 중복 점수 등을 저장합니다.
