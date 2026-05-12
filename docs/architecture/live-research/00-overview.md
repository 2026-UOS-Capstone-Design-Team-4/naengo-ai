# 00. Live Research Overview

Live Research는 내부 DB에 없거나 최신성이 중요한 요리 정보를 외부 웹에서 조사해 답변에 보강하는 계층이다.

AI Agent가 직접 웹을 다루지 않고 `LiveResearchService`를 호출하는 구조로 둔다.

## Target Flow

```text
User Message
  -> IntentClassifier
  -> AgentRouter
      -> RecipeRetrievalService
      -> LiveResearchService
          -> SourcePolicy
          -> SearchProvider
          -> PageFetcher
          -> ContentExtractor
          -> EvidenceSummarizer
          -> CitationBuilder
```

## When To Use

- 최신 유행 레시피
- SNS에서 뜨는 요리
- 시즌/이벤트성 메뉴
- 최근 식품 트렌드
- 내부 DB 검색 결과가 부족하고 최신성이 중요한 경우

## When Not To Use

- 일반 냉장고 재료 기반 추천
- DB에 충분한 레시피 후보가 있는 경우
- 사용자 프로필만으로 해결 가능한 질문
- 검증이 어려운 의학/질병/치료 수준의 영양 조언
- 출처 표시 없이 원문을 길게 재사용해야 하는 요청

## Agent Boundary

```text
AgentService
  -> AgentRouter
      -> LiveResearchService.research(query, context)
```

Agent는 research 결과의 요약과 citation만 사용한다. 검색 provider, 페이지 파싱, 캐싱은 LiveResearchService 내부 책임이다.

## Subdocuments

- [01. Source Policy](01-source-policy.md)
- [02. Research Flow](02-research-flow.md)
- [03. Agent Integration](03-agent-integration.md)
- [04. Safety and Caching](04-safety-and-caching.md)
