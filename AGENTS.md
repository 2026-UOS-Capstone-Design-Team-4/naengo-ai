# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 커밋 컨벤션

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능에 대한 커밋 |
| `fix` | 버그 수정에 대한 커밋 |
| `build` | 빌드 관련 파일 수정 / 모듈 설치 또는 삭제에 대한 커밋 |
| `chore` | 그 외 자잘한 수정에 대한 커밋 |
| `ci` | CI 관련 설정 수정에 대한 커밋 |
| `docs` | 문서 수정에 대한 커밋 |
| `style` | 코드 스타일 혹은 포맷 등에 관한 커밋 |
| `refactor` | 코드 리팩토링에 대한 커밋 |
| `test` | 테스트 코드 수정에 대한 커밋 |
| `perf` | 성능 개선에 대한 커밋 |

- 커밋 메시지는 한국어로 작성합니다.
- 커밋 시 파일을 하나씩 나눠서 커밋합니다. 여러 파일을 한 번에 커밋하지 않습니다.
- 기능 단위로 커밋하며, `uv.lock` 파일도 함께 커밋해 주세요.

## Push 전 체크리스트

- push 전에 `README.md`의 내용(프로젝트 구조, 기술 스택, 환경 변수 등)이 실제 코드와 일치하는지 확인하고, 불일치가 있으면 수정합니다.

## 설계 문서

구현 전에 반드시 관련 설계 문서를 먼저 읽습니다.

- 전체 설계 지도: [`architecture.md`](architecture.md)
- 문서 목록 및 읽기 순서: [`docs/00-index.md`](docs/00-index.md)

### 주요 설계 문서

| 영역 | 문서 |
|------|------|
| API 전체 구조 | [`docs/architecture/api/00-overview.md`](docs/architecture/api/00-overview.md) |
| User API | [`docs/architecture/api/01-user-api.md`](docs/architecture/api/01-user-api.md) |
| Admin API | [`docs/architecture/api/02-admin-api.md`](docs/architecture/api/02-admin-api.md) |
| Internal API | [`docs/architecture/api/03-internal-api.md`](docs/architecture/api/03-internal-api.md) |
| 인증/권한 | [`docs/architecture/api/04-auth-and-permissions.md`](docs/architecture/api/04-auth-and-permissions.md) |
| 에러 응답 | [`docs/architecture/api/05-error-response.md`](docs/architecture/api/05-error-response.md) |
| DB 스키마 | [`docs/architecture/database/00-schema.md`](docs/architecture/database/00-schema.md) |
| Migration 전략 | [`docs/architecture/database/01-migration-strategy.md`](docs/architecture/database/01-migration-strategy.md) |
| 데이터 수집 파이프라인 | [`docs/architecture/data-ingestion/00-overview.md`](docs/architecture/data-ingestion/00-overview.md) |
| Admin 검수 흐름 | [`docs/architecture/admin-review/00-overview.md`](docs/architecture/admin-review/00-overview.md) |
| AI 에이전트 | [`docs/architecture/ai-agent/00-overview.md`](docs/architecture/ai-agent/00-overview.md) |
| Background Jobs | [`docs/architecture/background-jobs/00-overview.md`](docs/architecture/background-jobs/00-overview.md) |
| Live Research | [`docs/architecture/live-research/00-overview.md`](docs/architecture/live-research/00-overview.md) |

### 설계 원칙

- 새 테이블을 추가할 때는 `db/schema.sql`을 먼저 수정하고 SQLAlchemy 모델을 추가합니다. 순서를 바꾸지 않습니다.
- 에러 응답은 `{"error": {"code": "...", "message": "...", "details": {}}}` 형식을 따릅니다.
- HTTP 트리거 비동기 작업은 FastAPI `BackgroundTasks`를 사용합니다. 별도 큐/워커 인프라를 추가하지 않습니다.
- 배치 작업(스크래핑, 정규화, import, embedding 백필)은 CLI 스크립트로 구현합니다.
