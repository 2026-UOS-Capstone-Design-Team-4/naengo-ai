# 00. AI Agent Overview

AI Agent는 사용자의 채팅 입력을 해석하고, 필요한 경우 레시피 검색을 수행한 뒤, SSE 스트림으로 답변과 추천 레시피를 전달한다.

## Current Flow

```text
User Prompt
  -> PydanticAI Agent
  -> search_recipes tool
  -> RecipeRetrievalService
       -> EmbeddingService
       -> pgvector cosine distance query
  -> Recipe rows
  -> Agent response stream
  -> SSE message + recipes
```

## Target Flow

```text
ChatService
  -> AgentService
      -> IntentClassifier
      -> AgentRouter
      -> PromptBuilder
      -> UserContextBuilder
      -> RecipeSearchPlanner
      -> LiveResearchService
      -> ToolRegistry
      -> StreamEventBuilder
  -> RecipeRetrievalService
```

핵심 변화는 검색 전에 의도 분석을 먼저 수행하는 것이다. 모든 입력을 레시피 검색으로 보내지 않고, 요리 관련 여부와 요청 타입에 따라 route를 나눈다.

## Responsibilities

- 사용자 입력의 요리 관련 여부 판단
- 요청 타입 분류
- 사용자 프로필과 대화 이력 반영
- 레시피 검색 계획 생성
- 최신성이 중요한 질문에서 live research 사용 여부 결정
- tool 호출 경계 관리
- 답변 스트리밍 이벤트 생성
- 검색 결과와 일반 AI 답변 분리

## Subdocuments

- [01. Intent Analysis](01-intent-analysis.md)
- [02. Agent Service](02-agent-service.md)
- [03. Retrieval Planning](03-retrieval-planning.md)
- [04. Streaming Events](04-streaming-events.md)
- [05. Testing Strategy](05-testing-strategy.md)
- [Live Research](../live-research/00-overview.md)
