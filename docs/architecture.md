# Naengo AI Architecture

이 문서는 Naengo AI의 전체 설계 지도입니다. 구현 전에 이 문서를 먼저 읽고,
현재 작업과 직접 관련된 하위 문서만 추가로 확인합니다.

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

## 2. Documents & Reading Order

구현 전에 이 순서로 읽되, 현재 작업과 관련된 문서만 선택해서 읽습니다.

1. [Architecture Overview](architecture/00-overview.md)
2. [API Overview](architecture/01-api/00-overview.md)
3. [User API](architecture/01-api/01-user-api.md)
4. [Admin API](architecture/01-api/02-admin-api.md)
5. [Internal API](architecture/01-api/03-internal-api.md)
6. [Auth and Permissions](architecture/01-api/04-auth-and-permissions.md)
7. [Error Response](architecture/01-api/05-error-response.md)
8. [Data Ingestion Overview](architecture/02-data-ingestion/00-overview.md)
9. [Data Ingestion Schema](architecture/02-data-ingestion/01-schema.md)
10. [Data Ingestion Pipeline](architecture/02-data-ingestion/02-pipeline.md)
11. [Scraper Operations](architecture/02-data-ingestion/03-scraper-operations.md)
12. [Classification and Confidence](architecture/02-data-ingestion/06-classification-and-confidence.md)
13. [Database Schema](architecture/03-database/00-schema.md)
14. [Database Migration Strategy](architecture/03-database/01-migration-strategy.md)
15. [AI Agent Overview](architecture/04-ai-agent/00-overview.md)
16. [AI Intent Analysis](architecture/04-ai-agent/01-intent-analysis.md)
17. [AI Agent Service](architecture/04-ai-agent/02-agent-service.md)
18. [AI Retrieval Planning](architecture/04-ai-agent/03-retrieval-planning.md)
19. [AI Streaming Events](architecture/04-ai-agent/04-streaming-events.md)
20. [AI Testing Strategy](architecture/04-ai-agent/05-testing-strategy.md)
21. [AI Evaluation](architecture/04-ai-agent/06-evaluation.md)
22. [Live Research Overview](architecture/05-live-research/00-overview.md)
23. [Live Research Source Policy](architecture/05-live-research/01-source-policy.md)
24. [Live Research Flow](architecture/05-live-research/02-research-flow.md)
25. [Live Research Agent Integration](architecture/05-live-research/03-agent-integration.md)
26. [Live Research Safety and Caching](architecture/05-live-research/04-safety-and-caching.md)
27. [Background Jobs Overview](architecture/06-background-jobs/00-overview.md)

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

| Layer     | Responsibility                                                         |
| --------- | ---------------------------------------------------------------------- |
| Router    | HTTP request/response, dependency injection, status mapping            |
| Service   | Use case execution, transaction boundary, domain rules                 |
| Agent     | LLM orchestration, route decision, tool selection, response generation |
| Retrieval | Embedding generation, vector search, result normalization              |
| Ingestion | External/public recipe collection, staging, normalization, import      |
| Schema    | Public API contract                                                    |
| Model     | Database mapping                                                       |
| Config    | Environment and runtime settings                                       |

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
  architecture.md         # 전체 설계 지도 (이 파일)
  architecture/           # 세부 설계 문서
```

## 6. Current Public API

```text
POST   /api/v1/guest/chat

GET    /api/v1/chat/rooms
GET    /api/v1/chat/rooms/{room_id}
DELETE /api/v1/chat/rooms/{room_id}
POST   /api/v1/chat/rooms
POST   /api/v1/chat/rooms/{room_id}

GET    /api/v1/recipes?sort=latest|likes&cursor=...&limit=20
GET    /api/v1/recipes/scraps?cursor=...&limit=20
GET    /api/v1/recipes/{recipe_id}
POST   /api/v1/recipes/{recipe_id}/likes
DELETE /api/v1/recipes/{recipe_id}/likes
POST   /api/v1/recipes/{recipe_id}/scraps
DELETE /api/v1/recipes/{recipe_id}/scraps

GET    /api/v1/users/me
PATCH  /api/v1/users/me
DELETE /api/v1/users/me
GET    /api/v1/users/me/profile
POST   /api/v1/users/me/profile
DELETE /api/v1/users/me/profile

GET    /api/v1/user-recipes?cursor=...&limit=20
GET    /api/v1/user-recipes/{user_recipe_id}
POST   /api/v1/user-recipes/{user_recipe_id}/reports
GET    /api/v1/user-recipes/me
GET    /api/v1/user-recipes/me/{user_recipe_id}
POST   /api/v1/user-recipes/me
DELETE /api/v1/user-recipes/me/{user_recipe_id}

GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}
DELETE /api/v1/admin/chat-rooms/{room_id}

GET    /api/v1/admin/user-recipes?status=...&cursor=...
GET    /api/v1/admin/user-recipes/{user_recipe_id}
PATCH  /api/v1/admin/user-recipes/{user_recipe_id}
DELETE /api/v1/admin/user-recipes/{user_recipe_id}

GET    /api/v1/admin/user-recipe-reports?status=...&cursor=...
GET    /api/v1/admin/user-recipe-reports/{report_id}
PATCH  /api/v1/admin/user-recipe-reports/{report_id}
```

## 7. Near-Term Priorities

1. Keep SQLAlchemy models aligned with `db/schema.sql`.
2. Import public recipe data through staging scripts.
3. Rebuild recipe embeddings and classifications after import.
4. Improve AI agent retrieval quality and streaming behavior.
5. Add admin APIs later only when the script-first workflow becomes limiting.
