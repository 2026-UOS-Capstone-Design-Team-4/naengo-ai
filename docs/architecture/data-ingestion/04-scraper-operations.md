# 04. Scraper Operations

이 문서는 만개의레시피 scraper를 안정적으로 운영하기 위한 설계입니다.

## Goals

- 작은 샘플부터 안전하게 수집합니다.
- 중단 후 재시작할 수 있어야 합니다.
- 같은 URL을 반복 요청하지 않습니다.
- 실패 원인을 추적할 수 있어야 합니다.
- 수집, 파싱, 검수, import를 분리합니다.

## Job Types

```text
scrape-list
  -> 목록 페이지에서 recipe URL 후보 수집

scrape-detail
  -> 상세 페이지 fetch
  -> raw payload 생성
  -> recipe_sources 저장

parse
  -> raw payload를 staging tables로 추출
  -> recipe_source_extractions / ingredients / steps / labels 저장

review
  -> admin 검수
  -> APPROVED 또는 REJECTED

import
  -> APPROVED source를 production tables로 승격
```

`normalized_payload` 같은 중간 JSON을 억지로 만들지 않습니다. DB에 저장할 값은 목적별 staging 테이블에 바로 넣습니다.

## CLI Shape

초기 구현은 수동 CLI 실행을 기준으로 합니다.

```bash
uv run python scripts/scrape_10000recipe.py --limit 300 --delay-min 1 --delay-max 3
uv run python scripts/parse_recipe_sources.py --collection-status COLLECTED --limit 300
uv run python scripts/import_recipe_sources.py --review-status APPROVED --limit 300
```

옵션 후보:

| Option | Meaning |
| --- | --- |
| `--limit` | 이번 실행에서 처리할 최대 개수 |
| `--start-page` | 목록 수집 시작 페이지 |
| `--max-page` | 목록 수집 종료 페이지 |
| `--delay-min` | 요청 사이 최소 대기 초 |
| `--delay-max` | 요청 사이 최대 대기 초 |
| `--resume` | 기존 진행 상태 기준으로 재시작 |
| `--dry-run` | DB 저장 없이 파싱만 확인 |

## Rate Limit

초기 정책:

- 요청 사이 1~3초 랜덤 지연
- 상세 페이지 fetch 실패 시 exponential backoff
- 같은 URL은 한 run 안에서 재요청하지 않음
- HTTP 429, 403이 나오면 즉시 run 중단

## Resume Strategy

기본 resume 기준은 `recipe_sources`입니다.

```text
if source_site + source_recipe_id exists:
  skip
else:
  fetch and store
```

운영 화면에서 run 단위 추적이 필요해지면 `scraper_runs`를 추가합니다.

```text
scraper_runs
  id
  job_type
  source_site
  status
  start_page
  last_page
  requested_count
  collected_count
  parsed_count
  skipped_count
  failed_count
  started_at
  finished_at
  error_message
```

초기에는 별도 테이블 없이 CLI 로그와 `recipe_sources` 상태만으로 충분합니다.

## Failure Status

`recipe_sources`는 lifecycle 상태를 분리해서 저장합니다.

| Failure | Status |
| --- | --- |
| 상세 페이지 fetch 실패 | `collection_status = FAILED` |
| HTML 구조 변경으로 파싱 실패 | `parse_status = INVALID` |
| 필수 필드 부족 | `parse_status = REVIEW_REQUIRED`, `review_status = PENDING` |
| 중복 URL | 기존 row 유지, 새 요청은 skip |
| 이미지 업로드 실패 | `parse_status = REVIEW_REQUIRED`, `review_status = PENDING` |
| 권리 또는 품질 검토 필요 | `parse_status = REVIEW_REQUIRED`, `review_status = PENDING` |

## Logging

각 run은 아래 통계를 남깁니다.

```text
requested_count
collected_count
parsed_count
skipped_count
failed_count
duplicate_count
duration_seconds
```

로그에는 다음 정보를 포함합니다.

- `source_site`
- `source_url`
- `source_recipe_id`
- 실패 단계
- exception message
- retry count

## Raw Storage

초기에는 raw HTML 파일을 별도로 저장하지 않고, 파싱 결과 raw payload만 `recipe_sources.raw_payload`에 저장합니다.

HTML 원문 저장이 필요해지면 object storage에 저장합니다.

```text
storage/scraper/10000recipe/{source_recipe_id}.html
```

원문 HTML 저장은 용량과 권리 이슈가 있으므로 기본값으로 두지 않습니다.

## Implementation Order

1. `scrape_10000recipe.py`에서 100개 이하 샘플 수집
2. list/detail parser 테스트 작성
3. `recipe_sources` 저장
4. parse CLI 작성
5. admin review API 작성
6. import CLI 또는 import API 작성
7. 필요 시 `scraper_runs` 테이블 추가

CLI 스크립트와 HTTP 트리거 작업의 실행 전략 및 실패/재시도 정책은 [Background Jobs](../../background-jobs/00-overview.md)를 참고합니다.
