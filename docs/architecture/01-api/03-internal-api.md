# 03. Internal API

Internal API는 worker, scheduler, batch process가 호출하는 시스템 API다. 일반 사용자 화면이나 공개 admin 화면에서 직접 호출하지 않는다.

현재 ingestion은 CLI 중심으로 운영하므로 Internal API는 즉시 구현 대상이 아니다. scheduler, worker fleet, admin 자동화가 필요해지는 시점에 추가한다.

## Principles

- 네트워크 경계에서 내부 token 또는 secret으로 보호한다.
- 사용자 세션 API와 분리한다.
- 오래 걸리는 작업은 job id를 반환하고 비동기로 처리한다.
- 같은 작업이 여러 번 호출돼도 안전하도록 idempotency key 또는 domain 상태를 고려한다.
- HTTP request lifecycle에 AI 생성, 대량 import, embedding backfill 같은 긴 작업을 묶지 않는다.

## Deferred Jobs

예정 API:

```text
POST /api/v1/internal/jobs/import-foodsafetykorea-sources
POST /api/v1/internal/jobs/scrape-10000recipe-sources
POST /api/v1/internal/jobs/parse-recipe-sources
POST /api/v1/internal/jobs/import-approved-sources
POST /api/v1/internal/jobs/generate-recipe-images
POST /api/v1/internal/jobs/classification-backfill
POST /api/v1/internal/jobs/embedding-backfill
POST /api/v1/internal/jobs/live-research-cache-refresh
```

초기에는 CLI script 또는 scheduled command로 충분하다. API가 필요한 시점은 외부 scheduler, admin UI, worker fleet이 생기는 때다.

`pending-recipes/{id}/enrich`는 관리자가 화면에서 즉시 미리보는 기능에 가까우므로 초기 설계에서는 internal job으로 분리하지 않는다. 대량 보정이 필요해지면 별도 batch job으로 확장한다.

## Job Response

```json
{
  "job_id": "job_20260517_001",
  "status": "QUEUED",
  "accepted_at": "2026-05-17T10:00:00+09:00"
}
```

## Retry Targets

Internal job은 다음 실패를 재처리할 수 있다.

- `recipe_sources.parse_status = INVALID`
- `recipe_sources.parse_status = REVIEW_REQUIRED`
- `recipe_sources.import_status = FAILED`
- `recipe_image_generations.status = FAILED`
- storage upload 실패
- classification 생성 실패
- embedding 생성 실패
- live research cache 갱신 실패

수집 실패는 보통 `recipe_sources` row를 만들지 않으므로, scraper/import job 자체를 재실행한다.

## Relationship With Admin API

Admin API는 사람이 누르는 action이고, Internal API는 시스템이 반복 실행하는 action이다.

예시:

```text
admin calls POST /api/v1/admin/recipes/{id}/image-generations
  -> API creates recipe_image_generations row
  -> worker/internal job handles provider call and storage upload
  -> recipe_media and generation status are updated
```

이 구조로 가면 관리자 화면은 빠르게 응답하고, 실패/재시도는 job 시스템에서 관리할 수 있다.
