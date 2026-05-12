# 00. Background Jobs Overview

## 비동기 처리가 필요한 작업

| 작업 | 트리거 | 예상 소요 시간 | 비고 |
| --- | --- | --- | --- |
| 웹 스크래핑 | CLI | 수 분 ~ 수십 분 | rate limit 포함 |
| 정규화 / 검증 | CLI | 수 초 ~ 수 분 | |
| S3 이미지 업로드 | HTTP (import API) | 수 초 | 외부 네트워크 의존 |
| AI 이미지 생성 | HTTP (admin API) | 수 초 ~ 수십 초 | 비용 발생 |
| Embedding 생성 | HTTP (import API) | 수 초 | OpenAI API 호출 |
| recipe_sources import | HTTP (admin API) | 수 초 | 위 작업 포함 |
| Embedding 백필 | CLI | 수 분 ~ 수십 분 | 기존 레시피 대상 |

## 작업 유형 분류

### CLI Batch

관리자가 터미널에서 직접 실행하는 일괄 처리 작업. 응답 지연이 문제가 되지 않는다.

```text
scrape     웹 스크래핑
normalize  recipe_sources 정규화
import     READY 상태 recipe_sources → recipes
backfill   recipes embedding 백필
```

### HTTP 트리거

관리자 API 요청으로 시작되는 작업. HTTP 응답을 즉시 반환하고 실제 작업은 백그라운드에서 처리한다.

```text
POST /admin/recipe-sources/{id}/import
  -> S3 이미지 업로드
  -> embedding 생성
  -> recipes 저장

POST /admin/recipes/{id}/image-generations
  -> AI 이미지 생성
  -> S3 업로드
  -> recipe_image_generations 저장
```

## Phase 1: 추가 인프라 없이 시작

### CLI Batch → 스크립트 직접 실행

```bash
uv run python scripts/scrape_10000recipe.py --limit 300
uv run python scripts/normalize_recipe_sources.py --status COLLECTED --limit 300
uv run python scripts/import_recipe_sources.py --status READY --limit 300
uv run python scripts/backfill_embeddings.py --limit 500
```

각 스크립트는 독립적으로 실행 가능하고, 중단 후 재실행해도 안전하다. `recipe_sources.status`가 진행 상태를 추적한다.

### HTTP 트리거 → FastAPI BackgroundTasks

```python
from fastapi import BackgroundTasks

@router.post("/{source_id}/import")
async def import_recipe_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 선행 조건 검증 (동기)
    source = recipe_source_service.get_ready_source(source_id, db)

    # HTTP 응답 즉시 반환
    background_tasks.add_task(import_service.run, source_id)
    return {"status": "accepted", "source_id": source_id}
```

`BackgroundTasks`는 별도 프로세스나 큐 없이 같은 프로세스 내에서 비동기로 실행된다. 추가 인프라가 필요 없다는 장점이 있지만 서버 재시작 시 작업이 사라진다.

### Job 상태 추적 (Phase 1)

`recipe_sources.status` 필드로 진행 상태를 추적한다. import 중 실패는 `REVIEW_REQUIRED`로 되돌리고 `validation_errors`에 실패 이유를 남긴다.

AI 이미지 생성 상태는 `recipe_image_generations.status`로 추적한다.

```text
PENDING → GENERATING → COMPLETED
                     → FAILED
```

## Phase 2: ARQ 또는 Celery 도입 시점

아래 조건 중 하나가 충족되면 외부 큐 기반 워커로 전환한다.

- job 목록 조회, 진행률, 완료 여부를 UI에서 확인해야 함
- 실패 시 자동 재시도가 필요함
- 동시에 여러 import 요청이 들어와 동시성 제어가 필요함
- 서버 재시작 시 작업 유실이 허용되지 않음

### 도구 비교

| | ARQ | Celery |
| --- | --- | --- |
| 브로커 | Redis | Redis / RabbitMQ |
| 비동기 | asyncio 기반 | 동기 / async 혼용 |
| 설정 복잡도 | 낮음 | 높음 |
| 모니터링 | 기본 제공 없음 | Flower |
| 현재 스택 적합성 | FastAPI async와 잘 맞음 | 범용 |

FastAPI + SQLAlchemy async 스택이라면 ARQ가 더 자연스럽다. 단, 현재는 SQLAlchemy 동기 세션을 사용 중이므로 전환 시 세션 방식도 함께 검토한다.

## 실패 / 재시도 정책

| 작업 | 실패 처리 | 재시도 |
| --- | --- | --- |
| S3 이미지 업로드 | `recipe_sources.validation_errors`에 기록 | 관리자가 retry API 호출 |
| AI 이미지 생성 | `recipe_image_generations.status = FAILED` | 관리자가 재생성 API 호출 |
| Embedding 생성 | `recipe_sources.status = REVIEW_REQUIRED` | CLI backfill 스크립트로 재처리 |
| 스크래핑 | 로그 출력, 다음 URL 계속 진행 | `--resume` 플래그로 중단 지점 재시작 |

## 비용이 큰 작업 안전장치

### AI 이미지 생성

- HTTP 요청당 1개의 이미지 생성만 허용
- 동일 `recipe_id`에 대해 `PENDING` 또는 `GENERATING` 상태가 이미 있으면 새 요청 거절
- 월별 생성 횟수 제한은 Phase 2에서 `recipe_image_generations` 집계로 구현

### Embedding 생성

- import API에서 embedding은 트랜잭션 외부에서 먼저 생성 후 DB insert
  (실패 시 API 에러 반환, DB에 불완전한 row 남지 않음)
- 백필 스크립트는 `--limit` 플래그로 한 번에 처리하는 개수 제한
