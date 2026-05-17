# 00. Data Ingestion Overview

Data ingestion은 외부 레시피 원본을 Naengo 서비스용 정식 레시피로 바꾸는 파이프라인이다. 원본은 항상 `recipe_sources.raw_payload`에 보관하고, 파싱 결과는 `recipe_source_extractions*` staging 테이블에 저장한 뒤, 승인된 source만 `recipes*` production 테이블로 import한다.

## Current Sources

| Source | Purpose | Identity |
| --- | --- | --- |
| foodsafetykorea 공공데이터 | 초기 대량 레시피, 구조화된 영양 정보 | `source_type = PUBLIC_DATA`, `source_site = foodsafetykorea`, `parser_type = DATASET` |
| 만개의레시피 | 실제 사용자형 레시피 표현, 조리 흐름, 이미지 출처 | `source_type = WEB_SCRAPE`, `source_site = 10000recipe`, `parser_type = HTML` |

foodsafetykorea는 `../open-recipe/data/recipes.json`을 `scripts/import_foodsafetykorea_sources.py`로 `recipe_sources`에 적재한다. 만개의레시피는 `scripts/scrape_10000recipe.py`가 목록/상세 HTML을 읽어 raw payload를 만든다.

## Main Flow

```text
external dataset / web page
  -> recipe_sources(raw payload + source metadata)
  -> source-specific extraction script
  -> recipe_source_extractions
  -> recipe_source_extracted_ingredients
  -> recipe_source_extracted_steps
  -> recipe_source_extracted_labels
  -> recipe_source_quality_scores
  -> review_status = APPROVED
  -> import_approved_recipe_sources.py
  -> recipes / recipe_ingredients / recipe_steps / recipe_labels / recipe_nutrition
  -> backfill_recipe_classifications.py
  -> recipe_classifications / recipe_quality_scores
  -> recipe_embeddings
```

## Stage Boundaries

- `recipe_sources`: 원본 보관소다. 수집된 원문, 출처 식별자, parse/review/import 상태를 가진다.
- `recipe_source_extractions*`: 정식 recipe가 되기 직전의 staging 결과다. source별 파서, rule, AI 추정, Naengo 문체 rewrite 결과가 여기에 들어간다.
- `recipe_source_quality_scores`: staging 품질과 confidence를 기록한다. 추정한 필드, 검증 요약, source별 note를 포함한다.
- `recipes*`: 서비스에서 직접 조회하는 production 데이터다. 승인된 extraction만 이쪽으로 이동한다.
- `recipe_classifications`: 추천/검색/rerank용 분류 축이다. import 이후 별도 backfill로 만든다.
- `recipe_media` / `recipe_image_generations`: 서비스 노출 이미지와 AI 생성 이력이다. 원본 source 이미지 URL은 production media로 바로 복사하지 않는다.

## Text And Metadata Policy

foodsafetykorea와 만개의레시피 parser는 extraction 생성 단계에서 이미 Naengo staging format으로 정리한다. `recipe_sources.extraction_version`이 다음 값이면 import 단계에서 text rewrite를 다시 하지 않는다.

- `foodsafetykorea-extraction-v1`
- `10000recipe-extraction-v1`

인분과 시간은 source에 명시된 값을 우선 사용한다. 명시값이 부족하면 rule 기반 추정을 먼저 시도하고, 부족한 경우 AI가 근거 기반으로 추정한다. 그래도 근거가 약하면 null로 둔다. 단, 현재 extraction validation은 `servings`와 `cooking_time_minutes`를 요구한다. source extraction 단계에서는 준비 시간과 조리 시간을 나누지 않고 전체 조리 시간만 저장한다.

## Image Policy

외부 원본 이미지 URL은 staging provenance로만 둔다.

```text
source image url
  -> recipe_source_extractions.source_main_image_url
  -> recipe_source_extracted_steps.source_image_url
  -> production import does not create recipe_media
```

서비스 대표 이미지는 별도 AI 생성/선택 플로우에서 `recipe_image_generations`와 `recipe_media`로 관리한다.

## Terms

- `scrape`: 외부 웹 페이지에서 source를 수집하는 작업
- `scrap`: 사용자가 레시피를 저장하는 서비스 기능
- `raw_payload`: 재처리 가능한 원본 JSON
- `extraction`: raw payload에서 뽑은 staging 레시피
- `classification`: 추천/검색에 쓰는 의미 기반 분류 값
- `confidence`: 자동 처리 결과를 얼마나 그대로 사용할 수 있는지 나타내는 운영 점수

## Subdocuments

- [01. Schema](01-schema.md)
- [02. Pipeline](02-pipeline.md)
- [03. Scraper Operations](03-scraper-operations.md)
- [04. Image Storage](04-images.md)
- [05. AI Image Generation](05-ai-image-generation.md)
- [06. Classification and Confidence](06-classification-and-confidence.md)
