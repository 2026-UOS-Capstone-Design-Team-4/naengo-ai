# Naengo AI (냉고 AI)

냉장고 속 재료와 사용자 취향을 바탕으로 레시피를 추천하는 PydanticAI 기반 FastAPI 서버입니다.

## 주요 기능

- **AI 레시피 추천**: PydanticAI와 pgvector 기반 유사도 검색으로 레시피를 추천합니다.
- **실시간 스트리밍 대화**: `StreamingResponse`와 SSE로 AI 응답을 실시간 전송합니다.
- **대화 이력 관리**: 채팅방과 메시지를 저장하고 기존 대화 맥락을 이어갑니다.
- **레시피 목록/상세 조회**: 최신순, 좋아요순 커서 페이지네이션과 단건 상세 조회를 제공합니다.
- **좋아요/스크랩**: 레시피 좋아요, 스크랩, 내 스크랩 목록 조회를 지원합니다.
- **사용자 프로필 관리**: 사용자 정보와 취향/알레르기 입력(`user_input`)을 관리합니다.
- **레시피 제출/승인**: 사용자가 제출한 레시피를 관리자가 검토하고 정식 레시피로 승격합니다.
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

### 3. 환경변수 설정

루트에 `.env` 파일을 만들고 필요한 값을 입력합니다.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/naengo_db
API_KEY=your_gateway_api_key
BASE_URL=https://factchat-cloud.mindlogic.ai/v1/gateway
MODEL_NAME=gpt-5.3-chat-latest
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small
TEMP_USER_ID=1
```

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

API 문서는 서버 실행 후 [http://localhost:8000/docs](http://localhost:8000/docs)에서 확인할 수 있습니다.

## Docker 실행

```bash
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

## 프로젝트 구조

```text
naengo-ai/
  app/
    agents/                 # AI Agent, tool, system prompt
    api/v1/
      endpoints/            # chat, recipes, users, pending-recipes
        admin/              # 관리자 전용 엔드포인트
      docs/                 # OpenAPI 문서 메타데이터와 예시
      deps.py               # 공통 dependency
    core/                   # 설정(config)
    db/                     # DB 세션과 초기화
    models/                 # SQLAlchemy 모델
    schemas/                # Pydantic 스키마
    services/               # 비즈니스 로직과 AI/RAG 서비스
  scripts/                  # DB 데이터 삽입 스크립트
  tests/                    # 테스트 코드
  .github/workflows/        # GitHub Actions CI/CD
  architecture.md           # 시스템 설계 문서
  Dockerfile
  docker-compose.yml
  pyproject.toml
```

## 주요 API

```text
GET    /api/v1/chat/rooms
POST   /api/v1/chat/rooms
POST   /api/v1/chat/rooms/{room_id}

GET    /api/v1/recipes?sort=latest|likes&cursor=...&limit=20
GET    /api/v1/recipes/{recipe_id}
POST   /api/v1/recipes/{recipe_id}/likes
DELETE /api/v1/recipes/{recipe_id}/likes
POST   /api/v1/recipes/{recipe_id}/scraps
DELETE /api/v1/recipes/{recipe_id}/scraps

GET    /api/v1/users/me
PATCH  /api/v1/users/me
GET    /api/v1/users/me/profile
PATCH  /api/v1/users/me/profile
GET    /api/v1/users/me/scraps

GET    /api/v1/pending-recipes
POST   /api/v1/pending-recipes
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}
```

## 개발 규칙

- Ruff로 lint와 format을 관리합니다.
- 기능 단위로 커밋합니다.
- 의존성 변경이 있으면 `uv.lock`을 함께 커밋합니다.
- 자세한 설계와 로드맵은 [architecture.md](architecture.md)를 참고합니다.
- 상세 설계 문서는 [docs/00-index.md](docs/00-index.md)에서 순서대로 확인할 수 있습니다.
