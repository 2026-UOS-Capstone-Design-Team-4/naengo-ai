# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
