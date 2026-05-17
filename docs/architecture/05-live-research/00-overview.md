# 00. Live Research Overview

Live Research는 DB의 오래된 정보로는 답하기 어려운 최신 요리 정보를 실시간으로 조사해 보강하는 계층이다.

AI Agent가 직접 웹을 다루지 않고 `LiveResearchService`를 호출하는 구조다.

## Flow

```text
User Message
  -> IntentClassifier
  -> IntentAgentRouter
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

- 최신 유행 음식
- SNS에서 뜨는 요리
- 시즌/이벤트성 메뉴
- 최근 식품 트렌드
- 기존 DB 검색 결과가 부족하고 최신성이 중요한 경우

## When Not To Use

- 일반 장르/재료 기반 추천
- DB에 충분한 맛있는 정보가 있는 경우
- 사용자 프로필만으로 해결 가능한 질문
- 검증이 어려운 의학/질병/치료 관련 영양 조언
- 출처 표시 없이 타 문서를 길게 요약해서 재사용하는 요청

## Agent Boundary

```text
AgentService
  -> IntentAgentRouter
      -> LiveResearchService.research(query, context)
```

Agent는 research 결과의 요약과 citation을 활용한다. 검색 provider, 페이지 파싱, 캐싱은 LiveResearchService 내부 책임이다.

## Subdocuments

- [01. Source Policy](01-source-policy.md)
- [02. Research Flow](02-research-flow.md)
- [03. Agent Integration](03-agent-integration.md)
- [04. Safety and Caching](04-safety-and-caching.md)
