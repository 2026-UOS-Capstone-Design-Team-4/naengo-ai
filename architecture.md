# Naengo AI Architecture

이 문서는 Naengo AI의 전체 설계 지도를 제공합니다. 상세 설계는
`docs/architecture/` 아래의 번호가 붙은 문서 폴더로 분리합니다.

## 1. Product Goal

Naengo AI는 사용자의 보유 재료, 냉장고 사진, 취향 정보를 바탕으로 레시피를
추천하는 AI 요리 어시스턴트 API 서버입니다.

핵심 기능:

- 채팅 기반 AI 레시피 추천
- pgvector 기반 유사 레시피 검색
- 레시피 목록/상세 조회
- 좋아요/스크랩
- 사용자 프로필과 취향 정보 관리
- 사용자 제출 레시피 관리
- 외부/공공 레시피 데이터 수집, 정규화, import

## 2. Documents

- [Docs Index](docs/00-index.md)
- [Architecture Overview](docs/architecture/00-overview.md)
- [API Overview](docs/architecture/01-api/00-overview.md)
- [User API](docs/architecture/01-api/01-user-api.md)
- [Admin API](docs/architecture/01-api/02-admin-api.md)
- [Internal API](docs/architecture/01-api/03-internal-api.md)
- [Auth and Permissions](docs/architecture/01-api/04-auth-and-permissions.md)
- [Error Response](docs/architecture/01-api/05-error-response.md)
- [Data Ingestion Overview](docs/architecture/02-data-ingestion/00-overview.md)
- [Data Ingestion Schema](docs/architecture/02-data-ingestion/01-schema.md)
- [Data Ingestion Pipeline](docs/architecture/02-data-ingestion/02-pipeline.md)
- [Scraper Operations](docs/architecture/02-data-ingestion/03-scraper-operations.md)
- [Image Storage](docs/architecture/02-data-ingestion/04-images.md)
- [AI Image Generation](docs/architecture/02-data-ingestion/05-ai-image-generation.md)
- [Classification and Confidence](docs/architecture/02-data-ingestion/06-classification-and-confidence.md)
- [Database Schema](docs/architecture/03-database/00-schema.md)
- [Database Migration Strategy](docs/architecture/03-database/01-migration-strategy.md)
- [AI Agent Overview](docs/architecture/04-ai-agent/00-overview.md)
- [AI Intent Analysis](docs/architecture/04-ai-agent/01-intent-analysis.md)
- [AI Agent Service](docs/architecture/04-ai-agent/02-agent-service.md)
- [AI Retrieval Planning](docs/architecture/04-ai-agent/03-retrieval-planning.md)
- [AI Streaming Events](docs/architecture/04-ai-agent/04-streaming-events.md)
- [AI Testing Strategy](docs/architecture/04-ai-agent/05-testing-strategy.md)
- [Live Research Overview](docs/architecture/05-live-research/00-overview.md)
- [Live Research Source Policy](docs/architecture/05-live-research/01-source-policy.md)
- [Live Research Flow](docs/architecture/05-live-research/02-research-flow.md)
- [Live Research Agent Integration](docs/architecture/05-live-research/03-agent-integration.md)
- [Live Research Safety and Caching](docs/architecture/05-live-research/04-safety-and-caching.md)
- [Background Jobs Overview](docs/architecture/06-background-jobs/00-overview.md)

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
  +-- Agent / Retrieval / Live Research
  |
  +-- Database / Storage / Import
```

| Layer | Responsibility |
| --- | --- |
| Router | HTTP request/response, dependency injection, status mapping |
| Service | Use case execution, transaction boundary, domain rules |
| Agent | LLM orchestration, route decision, tool selection, response generation |
| Retrieval | Embedding generation, vector search, result normalization |
| Ingestion | External/public recipe collection, staging, normalization, import |
| Schema | Public API contract |
| Model | Database mapping |
| Config | Environment and runtime settings |

## 5. Current Code Structure

```text
app/
  agents/                 # Agent routing, prompts, user context, stream events
  api/v1/
    endpoints/            # chat, recipes, users, user-recipes
    endpoints/admin/      # admin endpoints
    openapi/              # OpenAPI metadata and examples
    deps.py               # shared API dependencies
  core/                   # settings
  db/                     # SQLAlchemy session
  models/                 # SQLAlchemy models
  schemas/                # Pydantic schemas
  services/               # application, AI, RAG, import services
db/
  schema.sql              # rebuildable database schema
scripts/                  # scraping, parsing, staging import, backfill CLI
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
POST   /api/v1/users/me/profile
DELETE /api/v1/users/me/profile
GET    /api/v1/users/me/scraps?cursor=...&limit=20

GET    /api/v1/user-recipes
GET    /api/v1/user-recipes/{pending_recipe_id}
POST   /api/v1/user-recipes
DELETE /api/v1/user-recipes/{pending_recipe_id}

GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}
DELETE /api/v1/admin/chat-rooms/{room_id}

GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/import

GET    /api/v1/admin/user-recipes?status=...&cursor=...
GET    /api/v1/admin/user-recipes/{pending_recipe_id}
PATCH  /api/v1/admin/user-recipes/{pending_recipe_id}
DELETE /api/v1/admin/user-recipes/{pending_recipe_id}
```

## 7. Near-Term Priorities

1. Keep SQLAlchemy models aligned with `db/schema.sql`.
2. Import public recipe data through staging scripts.
3. Rebuild recipe embeddings and classifications after import.
4. Improve AI agent retrieval quality and streaming behavior.
5. Add admin APIs later only when the script-first workflow becomes limiting.
