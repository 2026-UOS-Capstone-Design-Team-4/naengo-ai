# 00. Architecture Overview

Naengo AI는 채팅 기반 레시피 추천 API 서버입니다. 사용자의 재료, 냉장고 사진, 취향 정보를 바탕으로 AI가 레시피를 추천하고, pgvector 검색으로 실제 DB 레시피를 연결합니다.

## Layers

```text
Client
  -> FastAPI Router
  -> Service Layer
  -> Agent / Retrieval / Database
```

| Layer | Responsibility |
| --- | --- |
| Router | HTTP 요청/응답, dependency 주입, status 변환 |
| Service | 유스케이스 실행, 트랜잭션 경계, 도메인 규칙 |
| Agent | LLM 실행, tool 호출, 응답 생성 |
| Retrieval | embedding 생성, 벡터 검색, 검색 결과 정리 |
| Ingestion | 외부 레시피 수집, 정규화, 검수, import |
| Model | DB 테이블 매핑 |
| Schema | 외부 API contract |

## Current Code Structure

```text
app/
  agents/
  api/v1/
  core/
  db/
  models/
  schemas/
  services/
db/
  schema.sql
  seeds/
scripts/
docs/
  architecture/
```

## Detailed Docs

- [API](api/00-overview.md)
- [Data Ingestion](data-ingestion/00-overview.md)
- [Database Schema](database/00-schema.md)
- [AI Agent](ai-agent/00-overview.md)
