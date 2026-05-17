# 02. Data Ingestion Pipeline

현재 ingestion은 script-first workflow로 운영한다. 관리자 UI/API가 완성되기 전까지는 CLI 실행 결과와 `recipe_sources` 상태 필드를 기준으로 수집, 파싱, 승인, import를 제어한다.

## End-To-End Flow

```text
1. Source collection
   - foodsafetykorea: import JSON dataset
   - 10000recipe: scrape web list/detail pages

2. Raw staging
   - insert recipe_sources
   - keep raw_payload and source identity

3. Extraction
   - parse raw_payload into recipe_source_extractions*
   - normalize ingredients, steps, labels
   - estimate metadata when source is incomplete
   - rewrite text into Naengo staging tone
   - create recipe_source_quality_scores

4. Validation
   - required fields
   - enum values
   - structure preservation
   - duplicate hints

5. Review gate
   - keep review_status = PENDING by default
   - mark selected rows APPROVED with admin flow or bulk script

6. Production import
   - import APPROVED + NOT_IMPORTED sources
   - create recipes, ingredients, steps, labels, nutrition
   - update imported_recipe_id and import_status

7. Post-import backfills
   - recipe_classifications
   - recipe_quality_scores
   - recipe_embeddings
   - AI image generation candidates
```

## Source Compatibility

모든 source는 같은 staging/import table을 사용한다.

| Source | Collect | Extract | Version |
| --- | --- | --- | --- |
| foodsafetykorea | `scripts/import_foodsafetykorea_sources.py` | `scripts/parse_foodsafetykorea_sources.py` | `foodsafetykorea-extraction-v1` |
| 10000recipe | `scripts/scrape_10000recipe.py` | `scripts/parse_10000recipe_sources.py` | `10000recipe-extraction-v1` |

foodsafetykorea는 `source_dataset_id + source_record_id`가 핵심 식별자다. 만개의레시피는 `source_site + source_recipe_id`와 `source_url`이 핵심 식별자다.

## Lifecycle Fields

`recipe_sources`는 lifecycle을 세 필드로 나눠 관리한다.

| Field | Values | Meaning |
| --- | --- | --- |
| `parse_status` | `NOT_PARSED`, `PARSED`, `INVALID`, `DUPLICATE`, `REVIEW_REQUIRED` | raw payload를 extraction으로 만들 수 있는지 |
| `review_status` | `PENDING`, `APPROVED`, `REJECTED` | production import를 허용할지 |
| `import_status` | `NOT_IMPORTED`, `IMPORTED`, `FAILED` | production table import 결과 |

수집 실패는 보통 row를 만들지 않는다. row가 생긴 뒤의 실패는 `parse_status`, `validation_errors`, `import_status`로 표현한다.

## Extraction Policy

### foodsafetykorea

- 재료 문자열은 `foodsafetykorea_ingredient_parser_service.py`가 Naengo ingredient schema로 구조화한다.
- 영양 정보는 원본 구조화 값이 있으면 `nutrition_source = SOURCE`로 보관한다.
- 인분/시간은 source 값 또는 recipe evidence 기반 추정을 사용한다.
- `servings`와 `cooking_time_minutes`가 없으면 invalid다.
- 준비 시간과 조리 시간은 source extraction 단계에서 따로 저장하지 않는다.

### 10000recipe

- HTML에서 제목, 설명, 재료, 단계, 작성자, 이미지 URL, tag를 raw payload로 만든다.
- parser는 raw payload를 staging table로 변환하고 Naengo 문체 rewrite를 적용한다.
- kcal_per_serving과 cooking_time_minutes는 source evidence 기반으로 추정할 수 있다.
- source extraction 단계에서는 전체 `cooking_time_minutes`만 저장한다.

## Text Rewrite Boundary

extraction version이 아래 값이면 import 단계에서 rewrite를 다시 하지 않는다.

- `foodsafetykorea-extraction-v1`
- `10000recipe-extraction-v1`

이 버전들은 extraction 단계에서 이미 Naengo staging format을 만든 것으로 본다. import 단계는 가능한 한 extraction 값을 그대로 production table로 옮긴다.

rewrite 대상:

- `title`, `summary`, `description`
- step `title`, `instruction`, `tip`
- label `TIP`

재료의 수량/단위 정규화는 source별 ingredient parser가 담당한다. text rewrite agent 응답에는 ingredients를 요구하지 않는다.

## Validation And Row Creation

parser가 invalid로 판단한 source는 extraction row를 만들지 않는다. 대신 `recipe_sources`에 다음 정보를 남긴다.

- `parse_status = INVALID`
- `review_status = PENDING`
- `validation_errors`
- `parsed_at`
- `extraction_version`

이 정책은 “invalid인데 extraction row가 있는 상태”를 피하기 위한 것이다.

AI metadata/rewrite 호출은 `RECIPE_IMPORT_AI_TIMEOUT_SECONDS` 안에 끝나야 한다. timeout, API 오류, rewrite 구조 검증 실패는 `INVALID`로 기록하고 다음 source 처리를 계속한다.

## Import Conditions

`scripts/import_approved_recipe_sources.py`는 다음 조건을 만족하는 source만 처리한다.

- `parse_status = PARSED`
- `review_status = APPROVED`
- `import_status = NOT_IMPORTED`
- extraction row가 존재함
- 필수 production 필드가 채워져 있음

import 중 실패하면 `import_status = FAILED`로 남기고 원인을 기록한다.

## Deduplication

중복 판단 우선순위:

1. DB unique constraint: `source_dataset_id + source_record_id`
2. DB unique constraint: `source_site + source_recipe_id`
3. DB unique constraint: `source_url`
4. `raw_content_hash`
5. `recipe_source_extractions.content_hash`
6. `title + normalized ingredients`
7. embedding similarity

스크래퍼는 기존 source를 기본적으로 skip한다. 그래도 동시성이나 세션 상태로 DB unique violation이 발생할 수 있으므로 저장 단계에서도 중복을 방어한다.

## Post-Import Jobs

classification과 embedding은 import와 분리한다.

```text
import_approved_recipe_sources.py
  -> backfill_recipe_classifications.py
  -> embedding backfill job
  -> optional image generation job
```

이렇게 분리하면 recipe 본문 import가 AI 분류/embedding 실패 때문에 막히지 않는다.
