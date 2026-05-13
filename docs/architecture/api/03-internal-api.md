# 03. Internal API

Internal API는 worker, scheduler, batch process가 호출하는 시스템 API입니다. 일반 관리자 화면에 직접 공개하지 않습니다.

## Principles

- 네트워크 경계에서 내부망 또는 secret으로 보호합니다.
- 사용자 액션 API와 분리합니다.
- 오래 걸리는 작업은 job id를 반환하고 비동기로 처리합니다.
- 같은 작업이 여러 번 호출되어도 안전하도록 idempotency key를 고려합니다.

## Jobs

```text
POST /api/v1/internal/jobs/scrape-recipes
POST /api/v1/internal/jobs/parse-recipe-sources
POST /api/v1/internal/jobs/import-approved-sources
POST /api/v1/internal/jobs/upload-recipe-media
POST /api/v1/internal/jobs/generate-recipe-images
POST /api/v1/internal/jobs/embedding-backfill
POST /api/v1/internal/jobs/live-research-cache-refresh
```

초기에는 CLI script 또는 scheduled worker로 충분합니다. API가 필요한 시점은 외부 scheduler, admin UI, worker fleet이 생기는 때입니다.

`pending-recipes/{id}/enrich`는 관리자가 화면에서 즉시 미리보는 기능이므로 초기 설계에서는 internal job으로 분리하지 않습니다. 대량 보정이 필요해지면 별도 batch job으로 확장합니다.

## Job Response

```json
{
  "job_id": "job_20260513_001",
  "status": "QUEUED",
  "accepted_at": "2026-05-13T10:00:00+09:00"
}
```

## Retry Targets

Internal job은 다음 실패를 재처리합니다.

- `recipe_sources.collection_status = FAILED`
- `recipe_sources.parse_status = INVALID`
- `recipe_sources.parse_status = REVIEW_REQUIRED`
- `recipe_sources.import_status = FAILED`
- 이미지 다운로드 실패
- S3 업로드 실패
- AI 이미지 생성 실패
- embedding 생성 실패
- live research cache 갱신 실패

## Relationship With Admin API

Admin API는 사람이 누르는 action입니다. Internal API는 시스템이 반복 실행하는 action입니다.

예시:

- 관리자가 `POST /admin/recipes/{id}/image-generations`를 호출
- API가 이미지 생성 job을 enqueue
- worker가 provider 호출, S3 업로드, `recipe_image_generations`와 `recipe_media` 갱신을 처리

이 구조로 가면 관리자 화면은 빠르게 응답하고, 실패/재시도는 job 시스템에서 관리할 수 있습니다.
