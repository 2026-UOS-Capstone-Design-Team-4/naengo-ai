# 01. Recipe Source Review

관리자는 `recipe_sources`의 raw/normalized 데이터를 비교하고, 정식 레시피로 올릴지 결정한다.

## Review List

목록에서 필요한 정보:

- `source_id`
- `source_type`
- `source_site`
- `source_url`
- `source_author_name`
- `status`
- `title` from `normalized_payload`
- `content_hash`
- `validation_errors`
- `collected_at`
- `parsed_at`
- `imported_at`

필터:

- status
- source site
- parser type
- collected date
- duplicate 여부
- validation error 존재 여부

정렬:

- 최신 수집순
- 오래된 수집순
- status별

## Review Detail

상세 화면에서 필요한 정보:

- raw payload
- normalized payload
- source metadata
- normalized metadata
- validation errors
- 중복 후보
- 이미지 원본 URL
- S3 업로드 결과
- import preview

## Editable Fields

관리자가 import 전에 수정할 수 있는 값:

- `title`
- `summary`
- `description`
- `ingredients`
- `ingredients_raw`
- `steps`
- `servings`
- `cooking_time`
- `difficulty`
- `category`
- `tags`
- `tips`
- `cuisine_type`
- `dish_type`
- `cooking_method`
- `main_ingredients`
- `taste_keywords`
- `image_url`
- `thumbnail_url`
- `image_urls`

수정 결과는 `recipe_sources.normalized_payload`, `normalized_metadata`에 반영한다.

## Duplicate Review

중복 후보는 아래 정보를 함께 보여준다.

- 기존 `recipe_id`
- 제목
- 주재료
- source URL
- similarity score
- content hash 일치 여부

관리자 선택:

- `REJECTED`: 새 데이터를 버림
- `READY`: 중복이 아니라고 판단하고 import
- `MERGED`: 기존 recipe에 일부 metadata만 병합

초기 구현에서는 `MERGED`는 보류하고 `REJECTED` 또는 `READY`만 지원한다.
