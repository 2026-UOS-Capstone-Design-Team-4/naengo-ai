# 00. Background Jobs Overview

Background job 문서는 오래 걸리거나 재시도가 필요한 작업을 어떤 실행 모델로 다룰지 정의한다. 현재는 script-first 운영이 우선이고, 나중에 worker 기반 job queue로 확장한다.

## Job Categories

| Job | Current Runner | Trigger | State |
| --- | --- | --- | --- |
| foodsafetykorea source import | CLI | 수동 | `recipe_sources` row |
| foodsafetykorea extraction | CLI | 수동 | `parse_status`, `validation_errors` |
| 10000recipe scrape | CLI | 수동 | `recipe_sources` row |
| 10000recipe extraction | CLI | 수동 | `parse_status`, `validation_errors` |
| approve for import | CLI/Admin 예정 | 수동 | `review_status` |
| production import | CLI | 수동 | `import_status`, `imported_recipe_id` |
| classification backfill | CLI | 수동 | `recipe_classifications`, `recipe_quality_scores` |
| embedding backfill | CLI 예정 | 수동 | `recipe_embeddings` |
| AI image generation | Admin API/worker 예정 | 수동 또는 예약 | `recipe_image_generations.status` |
| storage upload | image generation flow | 내부 호출 | `recipe_media` |

## Phase 1: CLI Batch

초기 운영은 CLI batch를 기준으로 한다.

```bash
uv run python scripts/import_foodsafetykorea_sources.py --input ../open-recipe/data/recipes.json
uv run python scripts/parse_foodsafetykorea_sources.py --limit 100 --refresh

uv run python scripts/scrape_10000recipe.py --limit 300 --delay-min 0.5 --delay-max 1.0
uv run python scripts/parse_10000recipe_sources.py --limit 300 --refresh

uv run python scripts/bulk_approve_sources.py --limit 300
uv run python scripts/import_approved_recipe_sources.py --limit 300
uv run python scripts/backfill_recipe_classifications.py --limit 300
```

각 script는 반복 실행 가능해야 한다.

- 이미 존재하는 source는 skip한다.
- `--refresh`가 있는 parser는 기존 extraction을 지우고 다시 만든다.
- invalid source는 extraction row를 만들지 않고 `parse_status = INVALID`로 남긴다.
- import는 `review_status = APPROVED`이고 `import_status = NOT_IMPORTED`인 source만 처리한다.

## Phase 1 State Tracking

현재 별도 job table은 없다. 상태는 domain table에 기록한다.

| Stage | State |
| --- | --- |
| source collected | `recipe_sources` row 존재 |
| parse/extraction | `recipe_sources.parse_status` |
| review gate | `recipe_sources.review_status` |
| production import | `recipe_sources.import_status` |
| image generation | `recipe_image_generations.status` |
| media availability | `recipe_media` row |
| embedding availability | `recipe_embeddings` row |

수집 실패는 보통 row를 만들지 않는다. row 생성 이후 실패는 parse/import/generation status로 표현한다.

## HTTP Trigger

관리자 UI에서 즉시 요청하는 작업은 FastAPI endpoint가 요청을 받고, 실제 긴 작업은 background task 또는 worker에 넘긴다.

예정 예시:

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations
  -> create recipe_image_generations(status = REQUESTED)
  -> enqueue generation job
```

FastAPI `BackgroundTasks`는 가벼운 초기 구현에는 쓸 수 있지만, 장시간 작업/재시도/관측성이 필요한 작업은 Phase 2 worker로 옮긴다.

## Phase 2: Worker Queue

반복 운영이 늘어나면 ARQ 또는 Celery 같은 worker queue를 도입한다.

필요 조건:

- job id와 status를 관리자 화면에서 확인할 수 있어야 한다.
- 실패 원인과 retry count를 저장해야 한다.
- 긴 작업이 HTTP request lifecycle에 묶이면 안 된다.
- 비용이 드는 AI 작업은 rate limit과 concurrency limit을 가져야 한다.

후보:

| | ARQ | Celery |
| --- | --- | --- |
| Broker | Redis | Redis / RabbitMQ |
| Runtime | asyncio 친화적 | sync/async 모두 가능 |
| FastAPI 궁합 | 좋음 | 보통 |
| 모니터링 | 직접 구현 필요 | Flower 등 생태계 큼 |

현재 FastAPI async 구조와 잘 맞는 쪽은 ARQ지만, 운영 도구와 팀 경험에 따라 Celery도 가능하다.

## Failure And Retry

| Job | Failure State | Retry |
| --- | --- | --- |
| foodsafetykorea import | 중복 record skip | 같은 명령 재실행 |
| 10000recipe scrape | 상세 페이지 실패는 skip, 403/429는 중단 | delay 조정 후 재실행 |
| extraction | `parse_status = INVALID` 또는 `REVIEW_REQUIRED` | source 수정 또는 `--refresh` |
| production import | `import_status = FAILED` | 원인 수정 후 재실행 |
| classification backfill | row 미생성 또는 낮은 confidence | backfill 재실행 |
| embedding backfill | `recipe_embeddings` row 없음 | backfill 재실행 |
| AI image generation | `recipe_image_generations.status = FAILED` | 새 generation 요청 |
| storage upload | generation 실패 처리 | image generation retry |

## Future Job Table

worker queue를 도입하면 source별 domain status와 별도로 job 실행 이력을 저장한다.

```text
background_jobs
  job_id
  job_type
  target_type
  target_id
  status
  requested_count
  processed_count
  skipped_count
  failed_count
  retry_count
  started_at
  finished_at
  error_message
  metadata
```

domain table은 “현재 데이터 상태”를, job table은 “실행 이력”을 담당한다.
