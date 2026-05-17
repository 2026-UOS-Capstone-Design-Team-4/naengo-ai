# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Docker 개발 환경

- 로컬 개발 컨테이너는 `docker compose -f docker-compose.dev.yml up -d --build`로 실행합니다.
- `docker-compose.dev.yml`은 소스 디렉터리를 `/app`에 bind mount하고 `uvicorn --reload`로 실행합니다.
- 일반적인 Python 코드 수정은 컨테이너에 바로 반영되므로 재빌드하지 않습니다. 의존성, Dockerfile, compose 설정이 바뀐 경우에만 재빌드합니다.

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
- 먼저 `architecture.md`에서 전체 구조와 문서 지도를 확인합니다.
- 그 다음 `docs/00-index.md`의 읽기 순서를 보고, 현재 작업과 직접 관련된 세부 문서만 추가로 읽습니다.
- 특정 문서 경로를 이 파일에 중복으로 나열하지 않습니다. 문서 구조가 바뀌면 `architecture.md`와 `docs/00-index.md`만 갱신합니다.
- 설계 문서는 구체적인 구현보다는 전체적인 흐름에 초점을 맞춥니다. 구현 세부사항은 코드에서 확인합니다.
