# 01. Recipe Source Review

관리자는 `recipe_sources`의 원본과 `recipe_source_extractions*`의 파싱 후보를 비교하고, 정식 레시피로 import할지 결정합니다.

## Review List

목록에서 필요한 정보:

- `source_id`
- `source_type`
- `source_site`
- `source_url`
- `source_author_name`
- `collection_status`
- `parse_status`
- `review_status`
- `import_status`
- `title` from `recipe_source_extractions`
- `raw_content_hash`
- `validation_errors`
- `collected_at`
- `parsed_at`
- `imported_at`

필터:

- collection status
- parse status
- review status
- import status
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

- `recipe_sources.raw_payload`
- `recipe_source_extractions`
- `recipe_source_extracted_ingredients`
- `recipe_source_extracted_steps`
- `recipe_source_extracted_labels`
- validation errors
- duplicate candidates
- source image URLs
- media upload result
- import preview

## Editable Fields

관리자가 import 전에 수정할 수 있는 값:

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
- ingredients
- steps
- labels
- classifications
- source image URLs

수정 결과는 `recipe_source_extractions*` 테이블에 반영합니다. `raw_payload`는 원본 백업이므로 수정하지 않습니다.

## Duplicate Review

중복 후보는 아래 정보를 함께 보여줍니다.

- 기존 `recipe_id`
- 제목
- 주재료
- source URL
- similarity score
- content hash 일치 여부

관리자 선택:

- `REJECTED`: 새 데이터를 버림
- `APPROVED`: 중복이 아니라고 판단하고 import 허용
- `MERGED`: 기존 recipe에 일부 정보만 병합

초기 구현에서는 `MERGED`는 보류하고 `REJECTED` 또는 `APPROVED`만 지원합니다.
