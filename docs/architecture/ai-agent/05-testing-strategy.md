# 05. Testing Strategy

AI Agent는 외부 LLM과 embedding API에 의존하므로 테스트에서 경계를 분리한다.

## Unit Tests

- `IntentClassifier`
- `AgentRouter`
- `RecipeSearchPlanner`
- `PromptBuilder`
- `StreamEventBuilder`

## Service Tests

- AgentService가 intent별 route를 올바르게 선택하는지 검증
- `OFF_TOPIC`이 retrieval을 호출하지 않는지 검증
- `RECIPE_RECOMMENDATION`이 planner와 retrieval을 호출하는지 검증
- `PROFILE_UPDATE`가 프로필 업데이트 후보로 분리되는지 검증

## Mock Strategy

- LLM response mock
- embedding vector mock
- retrieval result mock
- SSE event collector

## Example Cases

| Input | Expected Intent |
| --- | --- |
| `김치랑 두부 있는데 뭐 먹지?` | `RECIPE_RECOMMENDATION` |
| `새우 알레르기 있어` | `PROFILE_UPDATE` or `DIET_OR_ALLERGY` |
| `너 뭐 할 수 있어?` | `IDENTITY_OR_HELP` |
| `비트코인 시세 알려줘` | `OFF_TOPIC` |
| `양파 없으면 뭐로 대체해?` | `INGREDIENT_SUBSTITUTION` |

## Integration Tests

초기에는 실제 LLM을 호출하지 않는다. AgentService에 fake model/fake retrieval을 주입해 SSE 이벤트 순서와 DB 저장 여부만 검증한다.
