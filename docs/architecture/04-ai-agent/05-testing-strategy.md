# 05. Testing Strategy

AI Agent 테스트에서 LLM과 embedding API 의존성을 경계로 분리한다.

## Unit Tests

- `IntentClassifier`
- `IntentAgentRouter`
- `RecipeSearchPlanner`
- `ProfileUpdateExtractor`
- `ProfileUpdatePolicy`
- `StreamEventBuilder`

## Service Tests

- AgentService가 intent → route를 올바르게 선택하는지 검증
- `OFF_TOPIC`은 retrieval을 호출하지 않는지 검증
- `RECIPE_RECOMMENDATION`은 planner와 retrieval을 호출하는지 검증
- `PROFILE_UPDATE`가 새로운 업데이트 정보를 분리하는지 검증
- 명확한 1인칭 내 정보가 `AUTO_SAVE`로 결정되는지 검증
- 타인 정보, 임시 조건, 낮은 confidence 정보가 DB에 저장되지 않는지 검증
- 확인이 필요한 정보가 `REQUIRE_CONFIRMATION` 이벤트로 전달되는지 검증

## Mock Strategy

- LLM response mock
- embedding vector mock
- retrieval result mock
- SSE event collector

## Example Cases

| Input | Expected Intent |
| --- | --- |
| `김치랑 있는 거 뭐 먹어?` | `RECIPE_RECOMMENDATION` |
| `새우 알레르기 있어` | `PROFILE_UPDATE` or `DIET_OR_ALLERGY` |
| `너는 누구야?` | `IDENTITY` |
| `비트코인 시세 알려줘` | `OFF_TOPIC` |
| `파 없으면 뭐로 대체해?` | `INGREDIENT_SUBSTITUTION` |

## Profile Update Policy Cases

| Input | Expected Policy |
| --- | --- |
| `나 새우 알레르기 있어` | `AUTO_SAVE allergies += 새우` |
| `나는 고수 싫어요` | `AUTO_SAVE disliked_ingredients += 고수` |
| `15분 안에 하는 요리 주로 추천해줘` | `AUTO_SAVE preferred_cooking_time_minutes = 15` |
| `새우 알레르기 있는 친구가 있어` | `IGNORE` or `REQUIRE_CONFIRMATION`, no auto save |
| `오늘은 매운 거 싫어` | `IGNORE`, current turn context only |
| `당뇨 때문에 탄수화물을 줄여야 해` | `REQUIRE_CONFIRMATION` |
| `나는 매운 음식 좋아` (프로필에 매운 음식 싫어함 있는 경우) | `REQUIRE_CONFIRMATION` |

## Integration Tests

초기에는 실제 LLM을 호출하지 않는다. AgentService에 fake model/fake retrieval/fake profile service를 주입해 SSE 이벤트 시퀀스와 DB 저장 여부를 검증한다.
