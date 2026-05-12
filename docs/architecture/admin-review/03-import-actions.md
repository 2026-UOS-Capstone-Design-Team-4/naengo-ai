# 03. Import Actions

Import Action은 검수된 `recipe_sources`를 정식 레시피 테이블로 옮깁니다.

## Preconditions

`import`는 다음 조건을 만족해야 합니다.

- `recipe_sources.status = READY`
- `normalized_payload.recipe.title` 존재
- 재료와 조리 단계 존재
- `difficulty`가 `easy`, `normal`, `hard` 중 하나
- source URL 존재
- 중복 아님

대표 이미지는 권장 조건이지만 필수 조건은 아닙니다. 대표 이미지가 없으면 AI 이미지 생성 후보를 만들고 관리자 선택을 기다립니다.

## Write Set

생성/수정 대상:

- `recipes`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_stats`
- `recipe_sources`
- `recipe_image_generations`

## Transaction

하나의 트랜잭션으로 처리합니다.

```text
BEGIN
  INSERT recipes
  INSERT recipe_ingredients
  INSERT recipe_steps
  CREATE embedding
  UPDATE recipe_sources status/imported_recipe_id
COMMIT
```

대표 이미지가 없는 경우 AI 이미지 생성은 외부 API 호출이므로 DB 트랜잭션 밖에서 실행합니다.

```text
BEGIN
  recipe import
COMMIT
request AI image generation
store generated candidate
```

## Embedding Strategy

embedding 생성은 외부 API 호출이므로 두 가지 방식 중 하나를 선택합니다.

## Option A. Inline Embedding

트랜잭션 전에 embedding을 먼저 만듭니다.

```text
embedding 생성
BEGIN
  recipe insert
  source update
COMMIT
```

장점:

- DB 트랜잭션이 외부 API 호출을 기다리지 않습니다.

단점:

- embedding은 성공했지만 DB insert가 실패할 수 있습니다.

## Option B. Deferred Embedding

recipe를 먼저 만들고 embedding job을 나중에 수행합니다.

```text
BEGIN
  recipe insert with embedding = null
  source update
COMMIT
embedding backfill job
```

장점:

- import가 빠르고 안정적입니다.
- embedding 실패 재시도가 쉽습니다.

단점:

- embedding 없는 레시피는 벡터 검색에서 제외해야 합니다.

초기 추천은 Option A입니다. 구현이 단순하고 현재 규모에서 충분합니다.

## Representative Image Fallback

대표 이미지 보완 순서:

```text
source image
  -> S3 upload
  -> if missing or failed, request AI image generation
  -> store generated candidate
  -> admin select
  -> update recipes.image_url
```

초기 구현에서는 AI 생성 결과를 자동 노출하지 않고, `recipe_image_generations.status = SUCCEEDED` 후보로 저장합니다. 관리자가 후보를 선택하면 `SELECTED`로 바꾸고 `recipes.image_url`, `recipes.thumbnail_url`, `recipes.image_urls`를 갱신합니다.

## Failure Handling

| Failure | Handling |
| --- | --- |
| validation 실패 | `REVIEW_REQUIRED` |
| duplicate 발견 | `DUPLICATE` |
| DB insert 실패 | rollback |
| embedding 실패 | `REVIEW_REQUIRED` 또는 retry 대상 |
| 원본 image URL 없음 | import 후 AI 이미지 생성 후보 요청 |
| AI image generation 실패 | `recipe_image_generations.status = FAILED` |
| S3 upload 실패 | retry 대상 또는 `REVIEW_REQUIRED` |

## Audit

초기에는 `recipe_sources.updated_at`, `status`, `validation_errors`, `recipe_image_generations.status`로 충분합니다.

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
