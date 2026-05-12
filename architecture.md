# Naengo AI Architecture

이 문서는 Naengo AI의 전체 설계 지도를 제공한다. 상세 설계는 `docs/architecture/` 아래 문서로 분리한다.

## 1. Product Goal

Naengo AI는 사용자의 보유 재료, 냉장고 사진, 취향 정보를 바탕으로 레시피를 추천하는 AI 요리 어시스턴트 API 서버다.

핵심 기능:

- 채팅 기반 AI 레시피 추천
- pgvector 기반 유사 레시피 검색
- 레시피 목록/상세 조회
- 좋아요/스크랩
- 사용자 프로필과 취향 정보 관리
- 사용자 제출 레시피와 관리자 승인
- 외부 레시피 데이터 수집과 정규화

## 2. Documents

- [Docs Index](docs/00-index.md)
- [Architecture Overview](docs/architecture/00-overview.md)
- [API Overview](docs/architecture/api/00-overview.md)
- [User API](docs/architecture/api/01-user-api.md)
- [Admin API](docs/architecture/api/02-admin-api.md)
- [Internal API](docs/architecture/api/03-internal-api.md)
- [Auth and Permissions](docs/architecture/api/04-auth-and-permissions.md)
- [Error Response](docs/architecture/api/05-error-response.md)
- [Data Ingestion Overview](docs/architecture/data-ingestion/00-overview.md)
- [Data Ingestion Schema](docs/architecture/data-ingestion/01-schema.md)
- [Data Ingestion Pipeline](docs/architecture/data-ingestion/02-pipeline.md)
- [Image Storage](docs/architecture/data-ingestion/03-images.md)
- [Scraper Operations](docs/architecture/data-ingestion/04-scraper-operations.md)
- [AI Image Generation](docs/architecture/data-ingestion/05-ai-image-generation.md)
- [Database Schema](docs/architecture/database/00-schema.md)
- [Admin Review Overview](docs/architecture/admin-review/00-overview.md)
- [Recipe Source Review](docs/architecture/admin-review/01-recipe-source-review.md)
- [Review API](docs/architecture/admin-review/02-review-api.md)
- [Import Actions](docs/architecture/admin-review/03-import-actions.md)
- [Pending Recipe Enrichment](docs/architecture/admin-review/04-pending-recipe-enrichment.md)
- [AI Agent Overview](docs/architecture/ai-agent/00-overview.md)
- [AI Intent Analysis](docs/architecture/ai-agent/01-intent-analysis.md)
- [AI Agent Service](docs/architecture/ai-agent/02-agent-service.md)
- [AI Retrieval Planning](docs/architecture/ai-agent/03-retrieval-planning.md)
- [AI Streaming Events](docs/architecture/ai-agent/04-streaming-events.md)
- [AI Testing Strategy](docs/architecture/ai-agent/05-testing-strategy.md)
- [Live Research Overview](docs/architecture/live-research/00-overview.md)
- [Live Research Source Policy](docs/architecture/live-research/01-source-policy.md)
- [Live Research Flow](docs/architecture/live-research/02-research-flow.md)
- [Live Research Agent Integration](docs/architecture/live-research/03-agent-integration.md)
- [Live Research Safety and Caching](docs/architecture/live-research/04-safety-and-caching.md)
- [Database Migration Strategy](docs/architecture/database/01-migration-strategy.md)
- [Background Jobs Overview](docs/architecture/background-jobs/00-overview.md)

## 3. Technology Stack

- Runtime: Python 3.13
- API: FastAPI
- AI Agent: PydanticAI
- LLM Provider: OpenAI 호환 API Gateway
- Embedding: OpenAI Embedding API
- Database: PostgreSQL
- Vector Search: pgvector
- ORM: SQLAlchemy
- Settings: pydantic-settings
- Docs: scalar-fastapi
- Package Manager: uv
- Lint / Format: Ruff
- Infra: Docker, Docker Compose, AWS EC2, AWS RDS, GitHub Actions

## 4. Application Layers

```text
Client
  |
  v
FastAPI Router (app/api/v1/endpoints)
  |
  v
Service Layer (app/services)
  |
  +-- ChatService
  +-- RecipeService
  +-- UserService
  +-- PendingRecipeService
  +-- Ingestion / Import Services
  |
  +-- Agent (app/agents)
        |
        +-- Retrieval Service
              |
              +-- Embedding Service
              +-- pgvector query
```

| Layer | Responsibility |
| --- | --- |
| Router | HTTP request/response, dependency injection, status mapping |
| Service | Use case execution, transaction boundary, domain rules |
| Agent | LLM orchestration, tool selection, response generation |
| Retrieval | Embedding generation, vector search, result normalization |
| Ingestion | External recipe collection, validation, import |
| Schema | Public API contract |
| Model | Database mapping |
| Config | Environment and runtime settings |

## 5. Current Code Structure

```text
app/
  agents/                 # PydanticAI agent, dependencies, prompts
  api/v1/
    endpoints/            # chat, recipes, users, pending-recipes
    endpoints/admin/      # admin endpoints
    docs/                 # OpenAPI metadata
    deps.py               # shared API dependencies
  core/                   # settings
  db/                     # SQLAlchemy session
  models/                 # SQLAlchemy models
  schemas/                # Pydantic schemas
  services/               # application services
db/
  schema.sql              # rebuildable database schema
  seeds/                  # seed SQL files
scripts/
tests/
docs/
  architecture/           # detailed architecture documents
```

## 6. Current Public API

```text
GET    /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}
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
GET    /api/v1/users/me/scraps?cursor=...&limit=20

GET    /api/v1/pending-recipes
GET    /api/v1/pending-recipes/{pending_recipe_id}
POST   /api/v1/pending-recipes
DELETE /api/v1/pending-recipes/{pending_recipe_id}

GET    /api/v1/admin/recipes?video_url=...
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}
```

## 7. Near-Term Priorities

1. Align SQLAlchemy models with `db/schema.sql`.
2. Implement recipe source staging and import services.
3. Build a small 10000recipe scraper sample pipeline.
4. Add parser and import tests.
5. Improve AI agent design for retrieval quality, tool boundaries, and streaming events.
