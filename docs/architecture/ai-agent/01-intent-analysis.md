# 01. Intent Analysis

Intent Analysis Layer는 사용자의 입력이 요리 관련 질문인지 먼저 판단하고, 요청 타입을 분류한다.

## Goal

레시피 검색은 비용과 품질 모두에 영향을 주므로 모든 입력에 대해 바로 RAG 검색을 수행하지 않는다.

```text
User Message
  -> IntentClassifier
      -> cooking_related
      -> intent_type
      -> confidence
      -> reason
  -> AgentRouter
```

## Intent Result

```json
{
  "is_cooking_related": true,
  "intent_type": "RECIPE_RECOMMENDATION",
  "confidence": 0.92,
  "reason": "사용자가 보유 재료로 만들 수 있는 요리를 요청함"
}
```

## Intent Types

| Type | Meaning | Route |
| --- | --- | --- |
| `RECIPE_RECOMMENDATION` | 재료/상황 기반 추천 요청 | RecipeSearchPlanner |
| `RECIPE_DETAIL_QUESTION` | 특정 레시피에 대한 질문 | Conversation context + optional retrieval |
| `COOKING_TIP` | 조리 팁 질문 | Cooking answer |
| `INGREDIENT_SUBSTITUTION` | 대체 재료 질문 | Cooking answer + optional retrieval |
| `DIET_OR_ALLERGY` | 식단, 알레르기, 제한 조건 | User context + planner |
| `PROFILE_UPDATE` | 취향/알레르기 정보 갱신 후보 | Profile update flow |
| `IMAGE_BASED_RECIPE` | 이미지 기반 추천 | Image analysis + planner |
| `IDENTITY_OR_HELP` | 서비스 정체성/사용법 질문 | Fixed/lightweight answer |
| `SMALLTALK` | 가벼운 대화 | Short answer + cooking redirect |
| `OFF_TOPIC` | 요리와 무관한 질문 | Polite refusal / redirect |

## Two-Step Classifier

처음부터 모든 입력을 LLM 분류에 맡기지 않는다.

```text
RuleBasedFastPath
  -> obvious identity/help/smalltalk/off-topic
  -> otherwise LLMIntentClassifier
```

## Off-topic Policy

요리와 무관한 질문은 짧고 정중하게 범위를 안내한다.

예:

```text
저는 냉장고 재료와 요리 추천을 돕는 AI예요. 요리나 식재료 관련 질문을 해주시면 바로 도와드릴게요.
```

## Notes

- `confidence`가 낮으면 검색을 바로 수행하지 않고 명확화 질문을 우선한다.
- `PROFILE_UPDATE`는 바로 DB에 쓰지 않고 사용자 확인 또는 별도 정책을 둔다.
- `DIET_OR_ALLERGY`는 추천 planner에 강하게 반영한다.
