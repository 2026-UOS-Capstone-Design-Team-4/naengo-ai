# 00. Background Jobs Overview

## 비동기 처리가 필요한 작업

| 작업 | 트리거 | 예상 소요 시간 | 비고 |
| --- | --- | --- | --- |
| 레시피 스크래핑 | CLI | 수 분~수십 분 | rate limit 포함 |
| 파싱/검증 | CLI | 수 초~수 분 | staging tables 갱신 |
| S3 이미지 업로드 | HTTP 또는 worker | 수 초 | 외부 네트워크 의존 |
| AI 이미지 생성 | HTTP 또는 worker | 수 초~수십 초 | 비용 발생 |
| Embedding 생성 | HTTP 또는 worker | 수 초 | OpenAI API 호출 |
| source import | HTTP 또는 worker | 수 초 | 여러 테이블 write |
| Embedding backfill | CLI | 수 분~수십 분 | 기존 레시피 대상 |

## 작업 유형 분류

### CLI Batch

관리자가 서버에서 직접 실행하는 일괄 처리 작업입니다. 응답 지연이 문제되지 않습니다.

```text
scrape    외부 레시피 수집
parse     recipe_sources raw_payload 파싱
import    APPROVED recipe_sources를 recipes*로 승격
backfill  recipes embedding 재생성
```

### HTTP Trigger

관리자 API 요청으로 시작하는 작업입니다. HTTP 응답은 즉시 반환하고 실제 작업은 background에서 처리합니다.

```text
POST /admin/recipe-sources/{id}/import
  -> recipe_source_extractions* 검증
  -> S3 이미지 업로드
  -> recipes* 저장
  -> recipe_embeddings 생성 또는 enqueue

POST /admin/recipes/{id}/image-generations
  -> AI 이미지 생성
  -> S3 업로드
  -> recipe_image_generations 저장
  -> recipe_media 후보 저장
```

## Phase 1: 추가 인프라 없이 시작

### CLI Batch 스크립트 직접 실행

```bash
uv run python scripts/scrape_10000recipe.py --limit 300
uv run python scripts/parse_recipe_sources.py --collection-status COLLECTED --limit 300
uv run python scripts/import_recipe_sources.py --review-status APPROVED --limit 300
uv run python scripts/backfill_embeddings.py --limit 500
```

각 스크립트는 독립적으로 실행 가능하고, 중단 후 재실행해도 안전해야 합니다. 진행 상태는 `recipe_sources.collection_status`, `parse_status`, `review_status`, `import_status`로 추적합니다.

### HTTP Trigger는 FastAPI BackgroundTasks

```python
from fastapi import BackgroundTasks

@router.post("/{source_id}/import")
async def import_recipe_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    source = recipe_source_service.get_source(source_id)
    background_tasks.add_task(import_service.import_source, source.source_id)
    return {"status": "accepted", "source_id": source_id}
```

`BackgroundTasks`는 별도 프로세스 큐 없이 같은 프로세스 안에서 비동기로 실행됩니다. 추가 인프라가 필요 없다는 장점이 있지만, 서버 재시작 시 작업이 사라질 수 있습니다.

### Job 상태 추적

Phase 1에서는 별도 job table 없이 도메인 테이블의 상태 컬럼을 사용합니다.

- 수집: `recipe_sources.collection_status`
- 파싱: `recipe_sources.parse_status`
- 검수: `recipe_sources.review_status`
- import: `recipe_sources.import_status`
- AI 이미지: `recipe_image_generations.status`
- embedding: `recipe_embeddings` row 존재 여부

## Phase 2: ARQ 또는 Celery 전환 시점

아래 조건 중 하나가 충족되면 외부 큐 기반 worker로 전환합니다.

- job 목록 조회와 진행률 확인이 admin UI에 필요함
- 실패 후 자동 재시도가 필요함
- 동시에 여러 import 요청이 들어와 동시성 제어가 필요함
- 서버 재시작 후에도 작업 유실을 허용할 수 없음

### 도구 비교

| | ARQ | Celery |
| --- | --- | --- |
| Broker | Redis | Redis / RabbitMQ |
| 비동기 | asyncio 기반 | 동기 / async 혼용 |
| 설정 복잡도 | 낮음 | 높음 |
| 모니터링 | 기본 제공 약함 | Flower |
| 현재 스택 적합도 | FastAPI async와 잘 맞음 | 범용 |

현재 SQLAlchemy 동기 세션을 사용 중이므로 전환 전 세션 방식도 함께 검토합니다.

## 실패 / 재시도 정책

| 작업 | 실패 처리 | 재시도 |
| --- | --- | --- |
| S3 이미지 업로드 | `recipe_sources.validation_errors`에 기록 | 관리자 retry API 또는 media upload job |
| AI 이미지 생성 | `recipe_image_generations.status = FAILED` | 관리자 재생성 API |
| Embedding 생성 | `recipe_embeddings` row 미생성 | CLI backfill |
| 스크래핑 | 로그 출력, 다음 URL 계속 진행 | `--resume`으로 재시작 |

## 비용 작업 안전장치

### AI 이미지 생성

- HTTP 요청 1회에 1개의 이미지 생성만 허용
- 같은 `recipe_id`에 대해 `REQUESTED` 또는 `GENERATING` 상태가 있으면 새 요청 거절
- 월별 생성 횟수 제한은 Phase 2에서 `recipe_image_generations` 집계로 구현

### Embedding 생성

- import API에서는 embedding 생성 실패가 전체 import를 망치지 않게 분리합니다.
- backfill 스크립트는 `--limit` 플래그로 한 번에 처리하는 개수를 제한합니다.
