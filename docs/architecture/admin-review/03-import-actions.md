# 03. Import Actions

Import Action은 검수된 `recipe_source_extractions*` 후보를 정식 레시피 테이블로 옮깁니다.

## Preconditions

`import`는 다음 조건을 만족해야 합니다.

- `recipe_sources.collection_status = COLLECTED`
- `recipe_sources.parse_status = PARSED`
- `recipe_sources.review_status = APPROVED`
- `recipe_sources.import_status = NOT_IMPORTED`
- `recipe_source_extractions.title` 존재
- ingredients와 steps 존재
- `difficulty`가 `easy`, `normal`, `hard` 중 하나
- source URL 존재
- 중복 아님

대표 이미지는 권장 조건이지만 필수 조건은 아닙니다. 대표 이미지가 없으면 import 후 AI 이미지 생성 후보를 만들고 관리자 선택을 기다립니다.

## Write Set

생성/수정 대상:

- `recipes`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_labels`
- `recipe_classifications`
- `recipe_media`
- `recipe_embeddings`
- `recipe_quality_scores`
- `recipe_stats`
- `recipe_sources`
- `recipe_image_generations`

## Transaction

정식 레시피 승격은 하나의 DB 트랜잭션으로 처리합니다.

```text
BEGIN
  INSERT recipes
  INSERT recipe_ingredients
  INSERT recipe_steps
  INSERT recipe_labels
  INSERT recipe_classifications
  INSERT recipe_media
  UPDATE recipe_sources import_status/imported_recipe_id
COMMIT
```

외부 API 호출은 DB 트랜잭션 밖에서 수행합니다.

```text
embedding 생성
BEGIN
  recipe import
COMMIT
```

대표 이미지가 없는 경우 AI 이미지 생성도 트랜잭션 밖에서 실행합니다.

```text
BEGIN
  recipe import
COMMIT
request AI image generation
store generated candidate in recipe_media
```

## Embedding Strategy

embedding은 `recipe_embeddings`에 저장합니다.

초기 추천은 inline 생성입니다.

```text
embedding 생성
BEGIN
  recipe insert
  recipe_embeddings insert
  source update
COMMIT
```

대량 import가 필요해지면 deferred backfill로 전환합니다.

```text
BEGIN
  recipe insert without embedding
  source update
COMMIT
embedding backfill job
```

## Representative Image Fallback

대표 이미지 보완 순서:

```text
source image
  -> S3 upload
  -> recipe_media(image_role = MAIN, is_primary = true)
  -> if missing or failed, request AI image generation
  -> recipe_media(image_role = GENERATED_CANDIDATE)
  -> admin select
  -> recipe_media(image_role = MAIN, is_primary = true)
```

## Failure Handling

| Failure | Handling |
| --- | --- |
| validation 실패 | `parse_status = REVIEW_REQUIRED` |
| duplicate 발견 | `parse_status = DUPLICATE` |
| DB insert 실패 | rollback, `import_status = FAILED` |
| embedding 실패 | retry 대상 또는 backfill |
| 원본 image URL 없음 | import 후 AI 이미지 생성 후보 요청 |
| AI image generation 실패 | `recipe_image_generations.status = FAILED` |
| S3 upload 실패 | retry 대상 또는 review required |

## Audit

초기에는 `recipe_sources.updated_at`, lifecycle status, `validation_errors`, `recipe_image_generations.status`로 충분합니다.

나중에 필요하면 별도 history 테이블을 추가합니다.

```text
recipe_source_reviews
  review_id
  source_id
  admin_user_id
  action
  note
  before_status
  after_status
  created_at
```

import 중 발생하는 S3 업로드, embedding 생성 등 비동기 작업의 실행 전략은 [Background Jobs](../../background-jobs/00-overview.md)를 참고합니다.
