# 02. Agent Service

`AgentService`는 채팅 API와 PydanticAI agent 사이의 application boundary다.

## Responsibilities

- 채팅 메시지 수신 및 이력 관리
- intent classification 실행
- intent에 따른 route 결정
- prompt/context 구성
- agent 실행 및 SSE 이벤트 생성
- 검색된 레시피 결과 연결

## Flow

```text
AgentService
  -> IntentClassifier
  -> IntentAgentRouter
      RECIPE_RECOMMENDATION / DIET_OR_ALLERGY
        -> RecipeSearchPlanner
        -> RecipeRetrievalService (embedding + cosine cutoff)
        -> optional LiveResearchService
        -> Agent response with recipes

      COOKING_TIP / INGREDIENT_SUBSTITUTION / RECIPE_DETAIL_QUESTION
        -> Cooking answer
        -> optional retrieval

      PROFILE_UPDATE
        -> ProfileUpdateExtractor
        -> ProfileUpdatePolicy (AUTO_SAVE / REQUIRE_CONFIRMATION / IGNORE)
        -> UserProfileService

      IDENTITY / SMALLTALK
        -> lightweight answer

      OFF_TOPIC
        -> polite refusal
  -> StreamEventBuilder (SSE)
```

## Tool Boundary

Agent tool은 DB session이나 embedding client를 직접 다루지 않는다. `RecipeRetrievalService.search()`를 통해서만 검색한다.
