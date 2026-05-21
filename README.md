# Naengo AI

Naengo AI는 냉장고 속 재료, 사용자 취향, 대화 맥락을 바탕으로 레시피를 추천하는
FastAPI 기반 AI 요리 어시스턴트 서버입니다.

## 주요 기능

- **AI 레시피 추천**: PydanticAI 에이전트가 사용자 입력을 분석하고 레시피 추천, 일반 대화, 프로필 갱신 흐름으로 라우팅합니다.
- **RAG 기반 검색**: PostgreSQL + pgvector로 레시피 임베딩을 검색해 추천 후보를 구성합니다.
- **실시간 채팅 응답**: SSE로 채팅 응답과 추천 레시피를 스트리밍합니다.
- **레시피 서비스 API**: 레시피 목록/상세, 좋아요, 스크랩, 내 스크랩 목록을 제공합니다.
- **사용자 프로필 관리**: 취향, 알레르기, 식단 조건 등 추천에 필요한 사용자 정보를 관리합니다.
- **제출 레시피 검수**: 사용자가 제출한 레시피를 pending 상태로 관리하고, 관리자 검수 상태를 변경합니다.
- **관리자 API**: 관리자 레시피 목록, 제출 레시피 검수, 채팅방 삭제 기능을 제공합니다.
- **데이터 수집/정제**: 만개의레시피와 공공데이터 원천을 수집, 파싱, 검수, import하는 CLI 흐름을 제공합니다.
- **Live Research**: 설정이 켜진 경우 외부 검색 결과를 추천 보조 정보로 활용합니다.

## 기술 스택

- **Language**: Python 3.13
- **API**: FastAPI, Scalar API Reference
- **AI Agent**: PydanticAI
- **LLM / Embedding**: OpenAI API 호환 모델, OpenAI Embedding API
- **Database**: PostgreSQL, pgvector
- **ORM / Schema**: SQLAlchemy, Pydantic
- **Package Manager**: uv
- **Quality**: Ruff, pytest
- **Infra**: Docker, Docker Compose, AWS EC2, AWS RDS
- **CI/CD**: GitHub Actions

## 배포 현황

- `main` 브랜치에 push되면 GitHub Actions가 Docker 이미지를 빌드해 GHCR(`ghcr.io`)에 push한 뒤 EC2에 SSH로 접속해 배포합니다.
- 서버에서는 `~/naengo-deploy`의 `docker-compose.prod.yml`로 GHCR 이미지를 pull하고 컨테이너를 재시작합니다. 운영 서버에서 애플리케이션 이미지를 직접 빌드하거나 전체 git repo를 유지하지 않습니다.
- `~/naengo-deploy`에는 운영 비밀 파일인 `.env`와 `global-bundle.pem`이 있어야 하며, `docker-compose.prod.yml`은 배포 시 GitHub Actions가 복사합니다.
- 운영 컨테이너 이름은 `naengo-ai`, 포트는 `8000`입니다.
- 개발 환경은 `docker-compose.dev.yml`을 사용하며, 코드가 볼륨 마운트되어 일반적인 코드 수정 후 재빌드 없이 반영됩니다.
- API 문서는 서버 실행 후 `/docs`에서 확인합니다.
