# 01. Data Ingestion Schema

기준 DDL은 [db/schema.sql](../../../db/schema.sql)이다. 테이블 또는 컬럼을 바꿀 때는 `db/schema.sql`, SQLAlchemy model, schema, script를 함께 맞춘다.

## Design Principles

- 원본은 삭제하지 않고 `recipe_sources.raw_payload`에 JSON으로 보관한다.
- source별 파싱 결과는 production에 바로 넣지 않고 `recipe_source_extractions*` staging에 둔다.
- 검수/승인된 extraction만 `recipes*` production 테이블로 import한다.
- foodsafetykorea와 만개의레시피는 source 수집 방식만 다르고 같은 staging/import 흐름을 탄다.
- 추천/검색용 분류는 `recipe_classifications`로 분리한다.
- source 이미지 URL은 provenance로만 저장하고 production `recipe_media`로 자동 복사하지 않는다.
- embedding은 `recipe_embeddings`로 분리해 재생성 가능하게 둔다.

## Source Tables

### `recipe_sources`

외부 입력의 원본과 lifecycle 상태를 저장한다.

주요 컬럼:

- `source_type`: `PUBLIC_DATA`, `WEB_SCRAPE`, `VIDEO` 등 source 종류
- `source_site`: `foodsafetykorea`, `10000recipe` 같은 출처 namespace
- `parser_type`: `DATASET`, `HTML`, `AI`, `API`, `MANUAL`
- `source_recipe_id`: 웹 source의 레시피 ID
- `source_url`: 원본 URL
- `source_record_id`: dataset record ID
- `source_dataset_id`, `source_dataset_name`: 공공데이터 dataset 식별자
- `source_organization`: 제공 기관
- `source_author_name`, `source_author_url`: 웹 레시피 작성자 정보
- `raw_payload`: 재처리 가능한 원본 JSON
- `raw_content_hash`: 원본 payload hash
- `parse_status`: `NOT_PARSED`, `PARSED`, `INVALID`, `DUPLICATE`, `REVIEW_REQUIRED`
- `review_status`: `PENDING`, `APPROVED`, `REJECTED`
- `import_status`: `NOT_IMPORTED`, `IMPORTED`, `FAILED`
- `validation_errors`: parser/validator가 남긴 오류 목록
- `extraction_version`: extraction을 만든 parser 버전
- `collected_at`, `parsed_at`, `reviewed_at`, `imported_at`
- `imported_recipe_id`: import 후 생성된 `recipes.recipe_id`

중복 방어는 DB unique constraint로도 한다.

- 웹 source: `source_site + source_recipe_id`, `source_url`
- dataset source: `source_dataset_id + source_record_id`

### `recipe_source_extractions`

원본에서 추출한 레시피 본문 staging이다.

- 제목/요약/설명: `title`, `summary`, `description`
- 메타데이터: `servings`, `cooking_time_minutes`
- 영양: `kcal_per_serving`, `serving_weight_grams`, `carbohydrate_grams`, `protein_grams`, `fat_grams`, `sodium_milligrams`, `nutrition_source`, `nutrition_raw`
- 난이도: `difficulty`
- source media provenance: `source_main_image_url`, `source_thumbnail_url`, `source_video_url`
- 중복/변경 감지: `content_hash`

`nutrition_source`는 값의 출처를 나타낸다.

- `SOURCE`: 원본에 구조화되어 있던 값
- `RULE`: deterministic rule로 계산/정규화한 값
- `AI`: AI가 근거 기반으로 추정한 값
- `ADMIN`: 운영자가 수정한 값

### `recipe_source_quality_scores`

extraction 단계의 품질과 confidence를 저장한다. production의 `recipe_quality_scores`와 역할이 다르다.

- `completeness_score`: 필수 요소가 얼마나 채워졌는지
- `parse_confidence`: source parser 자체 신뢰도
- `ingredient_confidence`: 재료 파싱 신뢰도
- `metadata_confidence`: 인분/시간/난이도 등 메타데이터 신뢰도
- `rewrite_confidence`: Naengo 문체 rewrite 신뢰도
- `nutrition_confidence`: 영양 정보 신뢰도
- `estimated_fields`: AI/rule로 추정한 필드 목록
- `validation_summary`: validator 결과 요약
- `quality_notes`: source별 운영 메모

### `recipe_source_extracted_ingredients`

staging 재료 목록이다. `amount_text`는 사용자에게 보여줄 원문형 분량이고, `quantity`/`unit`은 가능한 경우만 구조화한다.

### `recipe_source_extracted_steps`

staging 조리 단계다. 원본 단계 이미지는 `source_image_url`에 provenance로 저장하고 production media로 자동 이동하지 않는다.

단계별 소요 시간, 온도, 도구는 현재 안정적으로 추출하지 않는다. 따라서 staging과 production step 테이블 모두 `step_no`, `instruction`, `tip`, 순서 정보 중심으로 유지하고, 필요해지면 별도 정책과 함께 컬럼을 추가한다.

### `recipe_source_extracted_labels`

staging label 목록이다.

- `label_type`: `TAG`, `TIP`, `CATEGORY`, `WARNING`
- `source`: `SCRAPE`, `RULE`, `AI`, `ADMIN`

## Production Tables

### `recipes`

서비스 노출용 정식 레시피 본문이다. `source_id`(FK)로 `recipe_sources`와 연결한다.

source 원본 정보(URL, 작성자, 라이선스 등)는 `recipes`에 복사하지 않고 `recipe_sources`에서 JOIN으로 읽는다. `source_id` FK는 `ON DELETE RESTRICT`라 recipe가 있는 source는 삭제할 수 없다.

### `recipe_ingredients`, `recipe_steps`, `recipe_labels`

정식 레시피의 반복 데이터다. extraction에서 검증된 순서와 구조를 유지해 import한다.

`recipe_steps`도 현재는 단계별 소요 시간, 온도, 도구를 저장하지 않는다.

### `recipe_nutrition`

상세 영양 정보 1:1 테이블이다. `recipes.kcal_per_serving`은 목록/상세에서 자주 쓰는 대표값으로 유지하고, 탄수화물/단백질/지방/나트륨 등은 이 테이블에 둔다.

### `recipe_classifications`

추천, 검색 필터, rerank에 쓰는 분류 축이다. import 이후 `scripts/backfill_recipe_classifications.py`가 생성한다.

### `recipe_media`

서비스에서 실제 사용하는 이미지/영상 media다. `image_role`은 `MAIN`, `THUMBNAIL`, `STEP`, `GALLERY`, `GENERATED_CANDIDATE` 중 하나다.

### `recipe_image_generations`

AI 이미지 생성 요청과 결과 이력이다. status는 `REQUESTED`, `GENERATING`, `SUCCEEDED`, `FAILED`, `SELECTED`, `REJECTED`를 사용한다.

### `recipe_embeddings`

pgvector 검색용 embedding이다. `embedding_type`으로 검색 목적을 구분한다.

### `recipe_quality_scores`

production recipe 기준 품질 점수다. extraction 품질 테이블과 달리 이미지 품질, instruction 품질, production classification confidence 등을 다룬다.
