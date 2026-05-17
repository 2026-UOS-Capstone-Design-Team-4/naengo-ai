# Naengo AI (냉고 AI)

냉장고 속 재료와 사용자 취향을 바탕으로 레시피를 추천하는 PydanticAI 기반
FastAPI 서버입니다.

## 주요 기능

- **AI 레시피 추천**: 의도 분류, 검색 계획, pgvector 유사도 검색으로 레시피를 추천합니다.
- **실시간 스트리밍 응답**: SSE로 AI 응답을 실시간 전송합니다. (`metadata -> message -> recipes -> done`)
- **대화 이력 관리**: 채팅방과 메시지를 저장하고 기존 대화 맥락을 이어갑니다.
- **레시피 목록/상세 조회**: 최신순, 좋아요순, 스크랩순 커서 페이지네이션과 단건 상세 조회를 제공합니다.
- **좋아요/스크랩**: 레시피 좋아요, 스크랩, 내 스크랩 목록 조회를 지원합니다.
- **사용자 프로필 관리**: 사용자 정보와 취향/알레르기 입력(`user_input`)을 관리합니다.
- **제출 레시피 검수**: 사용자가 제출한 레시피를 관리자가 검토하고 정식 레시피로 승격합니다.
- **데이터 수집 파이프라인**: 외부/공공 레시피 데이터를 staging에 적재하고 CLI로 import합니다.
- **API 문서**: Scalar 기반 API 문서를 제공합니다.

## 기술 스택

- **Backend**: FastAPI, PydanticAI
- **Database**: PostgreSQL, pgvector
- **ORM**: SQLAlchemy
- **Settings**: pydantic-settings
- **Package Manager**: uv
- **Infrastructure**: Docker, AWS EC2, AWS RDS
- **CI/CD**: GitHub Actions
- **Linting/Formatting**: Ruff

## 시작하기

### 1. uv 설치

Python 3.13 이상을 설치한 뒤 uv를 설치합니다.

```bash
pip install uv
uv --version
```

### 2. 의존성 설치

```bash
uv sync
```

### 3. 환경 변수 설정

루트에 `.env` 파일을 만들고 필요한 값을 입력합니다.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/naengo_db

# 채팅 AI (MindLogic Gateway)
API_KEY=your_gateway_api_key
BASE_URL=https://factchat-cloud.mindlogic.ai/v1/gateway
MODEL_NAME=gpt-5.4
RECIPE_IMPORT_REWRITE_ENABLED=true

# 임베딩 (OpenAI)
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small

# Live Research (선택)
LIVE_SEARCH_PROVIDER=disabled
BRAVE_SEARCH_API_KEY=
BRAVE_SEARCH_ENDPOINT=https://api.search.brave.com/res/v1/web/search
LIVE_SEARCH_TIMEOUT_SECONDS=5

TEMP_USER_ID=1
```

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

서버 실행 후 [http://localhost:8000/docs](http://localhost:8000/docs)에서
Scalar API 문서를 확인할 수 있습니다.

## Docker 실행

```bash
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml logs -f
docker compose -f docker-compose.dev.yml down

# production
docker compose -f docker-compose.prod.yml up -d --build
```

## 프로젝트 구조

```text
naengo-ai/
  app/
    agents/                 # intent, recipe agent, responder, core prompt 구성
    api/v1/
      endpoints/            # chat, recipes, users, pending-recipes
        admin/              # 관리자 전용 엔드포인트
      openapi/              # OpenAPI 문서 메타데이터와 예시
      deps.py               # 공통 dependency
    core/                   # 설정(config)
    db/                     # DB 세션과 초기화
    models/                 # SQLAlchemy 모델
    schemas/                # Pydantic 스키마
    services/               # 비즈니스 로직과 AI/RAG 서비스
  db/
    schema.sql              # 전체 DB 스키마 정의
    seeds/                  # 개발/테스트용 seed SQL
  scripts/                  # 데이터 수집과 import CLI 스크립트
  tests/                    # 테스트 코드
  architecture.md           # 시스템 설계 지도
  docs/                     # 상세 설계 문서
  Dockerfile
  docker-compose.dev.yml
  docker-compose.prod.yml
  pyproject.toml
```

## 주요 API

```text
# 채팅
GET    /api/v1/chat/rooms
POST   /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
POST   /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}

# 레시피
GET    /api/v1/recipes
GET    /api/v1/recipes/{recipe_id}
POST   /api/v1/recipes/{recipe_id}/likes
DELETE /api/v1/recipes/{recipe_id}/likes
POST   /api/v1/recipes/{recipe_id}/scraps
DELETE /api/v1/recipes/{recipe_id}/scraps

# 사용자
GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users/me/profile
PATCH  /api/v1/users/me/profile
GET    /api/v1/users/me/scraps

# 사용자 제출 레시피
GET    /api/v1/pending-recipes
POST   /api/v1/pending-recipes
GET    /api/v1/admin/pending-recipes
GET    /api/v1/admin/pending-recipes/{pending_recipe_id}
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}

# 관리자 레시피
GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}

# 관리자 수집 소스
GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/parse
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/import
```

## SSE 이벤트 (채팅 스트리밍)

| Event | Data | 설명 |
|-------|------|------|
| `room` | `{ "room_id": number }` | 새 채팅방 ID |
| `metadata` | `{ "intent_type": string, "model": string }` | 의도 분류와 실행 메타데이터 |
| `message` | `{ "content": string }` | AI 응답 chunk |
| `profile_update` | `{ "action": string, "candidates": array }` | 사용자 프로필 후보 처리 결과 |
| `recipes` | `Recipe[]` | 추천 레시피 목록 |
| `done` | `{ "message_id": number, "recipe_ids": number[] }` | 저장 완료 |
| `error` | `{ "code": string, "message": string }` | 오류 발생 |

## 개발 규칙

- Ruff로 lint와 format을 관리합니다.
- 기능 단위로 커밋하며, 의존성 변경이 있으면 `uv.lock`도 함께 커밋합니다.
- 자세한 설계는 [architecture.md](architecture.md)를 참고합니다.
- 상세 설계 문서는 [docs/00-index.md](docs/00-index.md)의 순서대로 확인합니다.
