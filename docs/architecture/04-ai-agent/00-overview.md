# 00. AI Agent Overview

AI Agent는 사용자의 채팅 입력을 해석하고, 필요한 경우 레시피 검색이나 live research를 수행해 SSE 스트림으로 답변과 추천 결과를 반환한다.

## Flow

```text
ChatService
  -> AgentService
      -> IntentClassifier       사용자 의도 분류
      -> IntentAgentRouter      intent에 따라 처리 경로 결정
      -> RecipeSearchPlanner    추천 요청 시 검색 쿼리/필터 구성
      -> RecipeRetrievalService embedding 검색 + cosine distance cutoff
      -> LiveResearchService    최신 정보가 필요한 경우 선택적 사용
      -> StreamEventBuilder     SSE 이벤트 생성
```

## Intent Routes

| Route | 설명 |
| --- | --- |
| `RECIPE_RECOMMENDATION` | 재료/상황 기반 레시피 추천 |
| `RECIPE_DETAIL_QUESTION` | 특정 레시피에 대한 질문 |
| `COOKING_TIP` | 조리 팁 질문 |
| `INGREDIENT_SUBSTITUTION` | 대체 재료 안내 |
| `DIET_OR_ALLERGY` | 식단, 알레르기, 식이 제한 반영 |
| `PROFILE_UPDATE` | 취향/알레르기 등 사용자 정보 갱신 |
| `IMAGE_BASED_RECIPE` | 이미지 기반 재료/레시피 추천 |
| `IDENTITY` | 서비스 자체나 사용법 질문 |
| `SMALLTALK` | 가벼운 일상 대화 |
| `OFF_TOPIC` | 요리와 무관한 질문 |

## Profile Update Policy

채팅 중 사용자 취향, 알레르기, 식이 제한 같은 정보가 발견되면 바로 DB에 쓰지 않고 정책에 따라 분류한다.

- `AUTO_SAVE`: 명확한 1인칭 본인 정보이고 allowlist 필드에 해당하면 자동 저장
- `REQUIRE_CONFIRMATION`: 주어가 모호하거나 기존 프로필과 충돌하면 사용자 확인 요청
- `IGNORE`: 타인 정보, 임시 조건, 농담 등은 저장하지 않음

## Live Research

DB 검색만으로 답하기 어려운 최신 트렌드, 최근 이슈, 외부 근거가 필요한 경우에만 선택적으로 사용한다. 기본 레시피 추천은 DB RAG 검색을 우선한다.

## Subdocuments

- [01. Intent Analysis](01-intent-analysis.md)
- [02. Agent Service](02-agent-service.md)
- [03. Retrieval Planning](03-retrieval-planning.md)
- [04. Streaming Events](04-streaming-events.md)
- [05. Testing Strategy](05-testing-strategy.md)
- [Live Research](../05-live-research/00-overview.md)
