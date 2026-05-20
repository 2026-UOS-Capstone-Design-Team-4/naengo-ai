# 00. Architecture Overview

Naengo AI는 채팅 기반 레시피 추천 API 서버입니다. 사용자의 보유 재료, 냉장고 사진, 취향 정보를 바탕으로 AI가 레시피를 추천하고, pgvector 검색으로 실제 DB 레시피와 연결합니다.

## Layers

```text
Client
  -> FastAPI Router
  -> Service Layer
  -> Agent / Retrieval / Database
```

| Layer | Responsibility |
| --- | --- |
| Router | HTTP 요청/응답, dependency 주입, status mapping |
| Service | use case 실행, transaction boundary, domain rule |
| Agent | LLM orchestration, route decision, response generation |
| Retrieval | embedding 생성, vector search, 결과 정규화 |
| Ingestion | 외부/공공 레시피 수집, staging, 정규화, import |
| Model | DB 테이블 mapping |
| Schema | public API contract |

## Current Code Structure

```text
app/
  agents/
    core/
    intent/
    recipe/
    responders/
  api/v1/
  core/
  db/
  models/
  schemas/
  services/
db/
  schema.sql
scripts/
docs/
  architecture/
```

## Current Design Notes

- 레시피 source는 공공데이터와 만개의레시피를 함께 사용합니다.
- source 원본은 staging에 보존하고, production import 전에 Naengo 문체로 재작성합니다.
- production import는 원본 이미지 URL을 `recipe_media`로 바로 복사하지 않습니다.
- S3는 AI 생성 이미지 저장을 중심으로 나중에 도입합니다.
- 관리자 UI/API는 user recipe와 production recipe 조회/검수에 사용합니다.
- source ingestion과 대량 import는 아직 script-first로 운영합니다.

## Detailed Docs

- [API](01-api/00-overview.md)
- [Data Ingestion](02-data-ingestion/00-overview.md)
- [Database Schema](03-database/00-schema.md)
- [AI Agent](04-ai-agent/00-overview.md)
- [Live Research](05-live-research/00-overview.md)
- [Background Jobs](06-background-jobs/00-overview.md)
