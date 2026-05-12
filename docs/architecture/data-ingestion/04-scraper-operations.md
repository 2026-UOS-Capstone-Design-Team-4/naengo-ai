# 04. Scraper Operations

이 문서는 만개의레시피 스크래퍼를 실제로 안정적으로 실행하기 위한 운영 설계다.

## Goals

- 작은 샘플부터 안전하게 수집한다.
- 중단 후 재시작할 수 있어야 한다.
- 같은 URL을 반복 요청하지 않는다.
- 실패 원인을 추적 가능하게 남긴다.
- 수집, 정규화, import를 분리한다.

## Job Types

```text
scrape-list
  -> 목록 페이지에서 recipe URL 후보 수집

scrape-detail
  -> 상세 페이지 HTML fetch
  -> raw payload 생성
  -> recipe_sources 저장

normalize
  -> raw payload를 공통 ingestion JSON으로 변환
  -> normalized_payload / metadata 저장

import
  -> READY source를 recipes / recipe_ingredients / recipe_steps로 승격
```

## CLI Shape

초기 구현은 수동 CLI 실행을 기준으로 한다.

```bash
uv run python scripts/scrape_10000recipe.py --limit 300 --delay-min 1 --delay-max 3
uv run python scripts/normalize_recipe_sources.py --status COLLECTED --limit 300
uv run python scripts/import_recipe_sources.py --status READY --limit 300
```

옵션 후보:

| Option | Meaning |
| --- | --- |
| `--limit` | 이번 실행에서 처리할 최대 개수 |
| `--start-page` | 목록 수집 시작 페이지 |
| `--max-page` | 목록 수집 종료 페이지 |
| `--delay-min` | 요청 간 최소 대기 초 |
| `--delay-max` | 요청 간 최대 대기 초 |
| `--resume` | 기존 진행 상태 기준으로 재시작 |
| `--dry-run` | DB 저장 없이 파싱만 확인 |

## Rate Limit

초기 정책:

- 요청 사이 1~3초 랜덤 딜레이
- 상세 페이지 fetch 실패 시 exponential backoff
- 같은 URL은 한 run 안에서 재요청하지 않음
- HTTP 429, 403이 나오면 즉시 run 중단

## Resume Strategy

기본 resume 기준은 `recipe_sources`다.

```text
if source_site + source_recipe_id exists:
  skip
else:
  fetch and store
```

추후 `scraper_runs` 테이블을 추가하면 더 정확히 관리할 수 있다.

```text
scraper_runs
  run_id
  job_type
  source_site
  status
  start_page
  last_page
  requested_count
  collected_count
  skipped_count
  failed_count
  started_at
  finished_at
  error_message
```

초기에는 테이블 없이 로그와 `recipe_sources` 상태만으로 충분하다.

## Failure Status

`recipe_sources.status`와 `validation_errors`를 사용한다.

| Failure | Status |
| --- | --- |
| 상세 페이지 fetch 실패 | `COLLECTED` 미생성 또는 retry log |
| HTML 구조 변경으로 파싱 실패 | `INVALID` |
| 필수 필드 부족 | `INVALID` |
| 중복 URL | `DUPLICATE` |
| 이미지 업로드 실패 | `REVIEW_REQUIRED` |
| 권리/품질 검수 필요 | `REVIEW_REQUIRED` |

## Logging

각 run은 아래 통계를 남긴다.

```text
requested_count
collected_count
skipped_count
failed_count
duplicate_count
duration_seconds
```

로그에는 다음 정보를 포함한다.

- `source_site`
- `source_url`
- `source_recipe_id`
- 실패 단계
- exception message
- retry count

## Raw Storage

초기에는 raw HTML 파일을 별도로 저장하지 않고, 파싱 결과 raw payload만 `recipe_sources.raw_payload`에 저장한다.

HTML 원문 저장이 필요해지면 다음 구조를 고려한다.

```text
storage/scraper/10000recipe/{source_recipe_id}.html
```

단, 원문 HTML 저장은 용량과 권리 이슈가 있으므로 기본값으로 두지 않는다.

## Implementation Order

1. `scrape_10000recipe.py`에서 100개 이하 샘플 수집
2. list/detail parser 테스트 작성
3. `recipe_sources` 저장
4. normalize CLI 작성
5. import CLI 작성
6. 필요 시 `scraper_runs` 테이블 추가

CLI 스크립트와 HTTP 트리거 작업의 실행 전략 및 실패/재시도 정책은 [Background Jobs](../../background-jobs/00-overview.md)를 참고합니다.
