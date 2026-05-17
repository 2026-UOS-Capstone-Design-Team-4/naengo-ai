# 03. Scraper Operations

이 문서는 foodsafetykorea dataset import와 만개의레시피 scraper를 script-first 운영 흐름에서 다루는 기준을 정리한다.

## Goals

- 외부 source를 동일한 `recipe_sources` staging interface로 모은다.
- 수집, 파싱, 승인, import를 분리해 실패 지점을 명확히 한다.
- 이미 수집한 source는 기본적으로 다시 요청하지 않는다.
- parser와 import는 idempotent하게 재실행할 수 있게 만든다.
- 초기 운영은 CLI와 DB 상태 필드를 기준으로 한다.

## Job Types

```text
foodsafetykorea-import
  -> JSON dataset read
  -> recipe_sources insert

foodsafetykorea-extract
  -> recipe_sources.raw_payload read
  -> ingredient parser agent
  -> metadata extractor
  -> text rewrite
  -> recipe_source_extractions* insert
  -> recipe_source_quality_scores insert

10000recipe-scrape
  -> list page fetch
  -> detail page fetch
  -> raw payload build
  -> recipe_sources insert

10000recipe-extract
  -> raw payload parse
  -> metadata estimate
  -> text rewrite
  -> recipe_source_extractions* insert
  -> recipe_source_quality_scores insert

approve-for-import
  -> mark reviewed source as APPROVED

import
  -> APPROVED source to production recipes*

post-import
  -> classifications, quality scores, embeddings, image generation candidates
```

## CLI Commands

```bash
uv run python scripts/import_foodsafetykorea_sources.py --input ../open-recipe/data/recipes.json
uv run python scripts/parse_foodsafetykorea_sources.py --limit 100 --refresh

uv run python scripts/scrape_10000recipe.py --limit 300 --delay-min 0.5 --delay-max 1.0
uv run python scripts/parse_10000recipe_sources.py --limit 300 --refresh

uv run python scripts/bulk_approve_sources.py --limit 300
uv run python scripts/import_approved_recipe_sources.py --limit 300
uv run python scripts/backfill_recipe_classifications.py --limit 300
```

## Options

| Option | Meaning |
| --- | --- |
| `--limit` | 이번 run에서 새로 처리할 최대 개수 |
| `--start-page` | 만개의레시피 목록 시작 페이지 |
| `--delay-min` | 상세 페이지 요청 사이 최소 대기 시간 |
| `--delay-max` | 상세 페이지 요청 사이 최대 대기 시간 |
| `--dry-run` | DB에 저장하지 않고 결과만 확인 |
| `--force` | 이미 수집된 recipe_id도 다시 요청 |
| `--refresh` | 기존 extraction을 지우고 다시 생성 |

현재 `scrape_10000recipe.py`는 `--max-page`를 지원하지 않는다. 페이지 범위 제한이 필요해지면 옵션을 추가한다.

AI 기반 parser/rewrite 호출은 환경 변수 `RECIPE_IMPORT_AI_TIMEOUT_SECONDS`를 timeout으로 사용한다. timeout이 발생한 source는 `INVALID`와 `PARSE_ERROR` 또는 `REWRITE_ERROR`로 남기고 batch 전체는 계속 진행한다.

## Resume Strategy

resume 기준은 별도 run table이 아니라 `recipe_sources`에 이미 저장된 source identity다.

```text
if source_site + source_recipe_id exists:
  skip
else:
  fetch detail page and save
```

스크래퍼는 저장 직전에도 DB unique violation을 방어한다. 목록 페이지에서 같은 recipe_id가 다시 보이거나 이전 run과 겹쳐도 전체 작업이 중단되지 않고 해당 row만 skip해야 한다.

긴 스크랩은 timeout될 수 있으므로 한 번에 너무 큰 `--limit`을 주기보다 200~500개 단위로 나눠 실행하는 편이 좋다. 이미 저장된 source는 skip되므로 같은 시작 페이지에서 재실행해도 된다.

## Rate Limit

운영 기본값:

- `--delay-min 0.5`
- `--delay-max 1.0`

더 보수적으로 운영해야 할 때는 1~3초를 사용한다.

HTTP 403 또는 429가 반복되면 즉시 중단하고 delay를 늘리거나 실행 시간을 나눈다. 실패한 상세 페이지는 row를 만들지 않는다.

## Status Handling

| Situation | Handling |
| --- | --- |
| 목록 페이지 fetch 실패 | 해당 page에서 ID를 얻지 못하면 run 종료 |
| 상세 페이지 fetch 실패 | 해당 recipe_id skip |
| HTTP 403/429 | run 중단 |
| HTML 구조 변경 | raw payload가 부족하면 parser에서 `INVALID` |
| 중복 source | 기존 row 유지, 새 저장 skip |
| extraction validation 실패 | extraction row 생성하지 않음, `parse_status = INVALID` |
| production import 실패 | `import_status = FAILED` |

수집 실패는 일반적으로 `recipe_sources` row를 만들지 않는다. row가 있는 source의 실패는 parse/import 상태로 표현한다.

## Current Local Seed Volumes

로컬 개발 DB에서 대량 테스트를 할 때의 기준 volume:

- foodsafetykorea: 전체 JSON 기준 1146개 source
- 10000recipe: 최소 1000개 source 확보

이 숫자는 운영 요구사항이 아니라 현재 개발/검증용 seed 규모다. 재수집 과정에서 목표보다 조금 더 많이 저장될 수 있으며, 중복이 아니라면 삭제하지 않는다.

## Logging

각 run은 최소한 다음 정보를 로그로 남긴다.

- requested limit
- saved count
- skipped duplicate count
- failed count
- current page
- source_recipe_id 또는 source_record_id
- exception message

향후 반복 운영이 필요해지면 `scraper_runs` 같은 run table을 추가한다.

```text
scraper_runs
  id
  job_type
  source_site
  status
  start_page
  last_page
  requested_count
  saved_count
  skipped_count
  failed_count
  started_at
  finished_at
  error_message
```

## Raw Storage

초기 구현은 raw HTML 파일을 별도 object storage에 저장하지 않는다. parser가 재처리할 수 있는 구조화 raw payload만 `recipe_sources.raw_payload`에 저장한다.

원본 HTML 보관이 필요해지면 다음 key 형태를 사용한다.

```text
storage/scraper/10000recipe/{source_recipe_id}.html
```

HTML은 용량, 저작권, 개인정보 이슈가 있을 수 있으므로 기본 보관 대상은 아니다.
