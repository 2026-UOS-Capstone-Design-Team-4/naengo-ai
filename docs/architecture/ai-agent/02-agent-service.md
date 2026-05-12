# 02. Agent Service

`AgentService`는 채팅 API와 PydanticAI Agent 사이의 application boundary다.

## Responsibility

- 채팅 메시지와 대화 이력 수신
- intent classification 실행
- intent에 따른 route 결정
- prompt/context 구성
- agent 실행
- SSE 이벤트 생성
- 검색된 레시피 결과 연결

## Target Structure

```text
AgentService
  -> IntentClassifier
  -> AgentRouter
  -> PromptBuilder
  -> UserContextBuilder
  -> RecipeSearchPlanner
  -> LiveResearchService
  -> ToolRegistry
  -> StreamEventBuilder
```

## AgentRouter

```text
RECIPE_RECOMMENDATION
  -> RecipeSearchPlanner
  -> RecipeRetrievalService
  -> optional LiveResearchService for fresh trends
  -> Agent response with recipes

COOKING_TIP / INGREDIENT_SUBSTITUTION
  -> Cooking answer
  -> optional retrieval

PROFILE_UPDATE
  -> Profile update candidate

IDENTITY_OR_HELP / SMALLTALK
  -> lightweight answer

OFF_TOPIC
  -> polite refusal
```

최신 유행, 최근 트렌드, DB에 없는 외부 근거가 필요한 경우에는 [Live Research](../live-research/00-overview.md)를 호출한다.

## Tool Boundary

Agent tool은 DB session이나 embedding client를 직접 다루지 않는다.

```text
Agent tool
  -> RecipeRetrievalService.search(...)
```

이렇게 두면 테스트와 모델 교체가 쉬워진다.
