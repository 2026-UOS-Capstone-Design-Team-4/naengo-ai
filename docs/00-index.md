# Naengo AI Docs

이 문서는 Naengo AI 설계 문서의 입구입니다. 구현 전에 `architecture.md`를 먼저 읽고, 필요한 영역의 하위 문서를 이어서 확인합니다.

## Architecture

- [00. Architecture Overview](architecture/00-overview.md)
- [API](architecture/01-api/00-overview.md)
- [Data Ingestion](architecture/02-data-ingestion/00-overview.md)
- [Database](architecture/03-database/00-schema.md)
- [AI Agent](architecture/04-ai-agent/00-overview.md)
- [Live Research](architecture/05-live-research/00-overview.md)
- [Background Jobs](architecture/06-background-jobs/00-overview.md)

## Reading Order

1. [Root Architecture](../architecture.md)
2. [Architecture Overview](architecture/00-overview.md)
3. [API Overview](architecture/01-api/00-overview.md)
4. [User API](architecture/01-api/01-user-api.md)
5. [Admin API](architecture/01-api/02-admin-api.md)
6. [Internal API](architecture/01-api/03-internal-api.md)
7. [Auth and Permissions](architecture/01-api/04-auth-and-permissions.md)
8. [Error Response](architecture/01-api/05-error-response.md)
9. [Data Ingestion Overview](architecture/02-data-ingestion/00-overview.md)
10. [Data Ingestion Schema](architecture/02-data-ingestion/01-schema.md)
11. [Data Ingestion Pipeline](architecture/02-data-ingestion/02-pipeline.md)
12. [Scraper Operations](architecture/02-data-ingestion/03-scraper-operations.md)
13. [Image Storage](architecture/02-data-ingestion/04-images.md)
14. [AI Image Generation](architecture/02-data-ingestion/05-ai-image-generation.md)
15. [Classification and Confidence](architecture/02-data-ingestion/06-classification-and-confidence.md)
16. [Database Schema](architecture/03-database/00-schema.md)
17. [Database Migration Strategy](architecture/03-database/01-migration-strategy.md)
18. [AI Agent Overview](architecture/04-ai-agent/00-overview.md)
19. [AI Intent Analysis](architecture/04-ai-agent/01-intent-analysis.md)
20. [AI Agent Service](architecture/04-ai-agent/02-agent-service.md)
21. [AI Retrieval Planning](architecture/04-ai-agent/03-retrieval-planning.md)
22. [AI Streaming Events](architecture/04-ai-agent/04-streaming-events.md)
23. [AI Testing Strategy](architecture/04-ai-agent/05-testing-strategy.md)
24. [Live Research Overview](architecture/05-live-research/00-overview.md)
25. [Live Research Source Policy](architecture/05-live-research/01-source-policy.md)
26. [Live Research Flow](architecture/05-live-research/02-research-flow.md)
27. [Live Research Agent Integration](architecture/05-live-research/03-agent-integration.md)
28. [Live Research Safety and Caching](architecture/05-live-research/04-safety-and-caching.md)
29. [Background Jobs Overview](architecture/06-background-jobs/00-overview.md)
