# 05. Testing Strategy

AI Agent 테스트에서 LLM과 embedding API 의존성을 경계로 분리한다.

## Unit Tests

- `MainIntentClassifier`
- `MainIntentResult`
- `DomainAnswerRouter`
- `ConversationMemoryBuilder`
- `AnswerVerifier`
- `AgentQualityWorkflow`
- `RecipeFindPlanner` (`RecipeSearchPlanner` 구현체 확장)
- `CookingQAPlanner`
- `AgentContextResolver`
- `ProfileUpdateAnalyzer`
- `ProfileUpdatePolicy`
- `StreamEventBuilder`

## Service Tests

- AgentService가 primary_task → planner → sub_intent → answer agent를 올바르게 선택하는지 검증
- AgentService가 short-term/long-term memory를 planner와 resolver에 전달하는지 검증
- `OFF_TOPIC`은 retrieval을 호출하지 않는지 검증
- `RECIPE_FIND`는 planner와 retrieval을 호출하는지 검증
- `COOKING_QA`는 레시피 참조 질문에서 context resolver를 호출하는지 검증
- `COOKING_QA`가 `needs_retrieval=true`인 경우 retrieval을 호출하는지 검증
- `COOKING_QA + SAFETY/RECIPE_CONTEXT/INGREDIENT_SUBSTITUTION`이 전용 answer agent로 라우팅되는지 검증
- 알레르기 포함 레시피가 verifier에서 감지되는지 검증
- 검증 성공 시 revision agent를 호출하지 않는지 검증
- 검증 실패 시 충돌 레시피를 제거하고 revision agent를 한 번만 호출하는지 검증
- 재검증 실패 시 빈 recipe payload와 안전 fallback을 반환하는지 검증
- 검증 전 생성 delta가 `message` 이벤트로 노출되지 않는지 검증
- `workflow` 이벤트의 stage/status/attempt 순서를 검증
- `PROFILE_MANAGEMENT`가 새로운 업데이트 정보를 분리하는지 검증
- 명확한 1인칭 내 정보가 `AUTO_SAVE`로 결정되는지 검증
- 타인 정보, 임시 조건, 낮은 confidence 정보가 DB에 저장되지 않는지 검증
- 확인이 필요한 정보가 `REQUIRE_CONFIRMATION` 이벤트로 전달되는지 검증

## Mock Strategy

- LLM response mock
- embedding vector mock
- retrieval result mock
- SSE event collector

## Golden Evaluation

챗봇 성능 개선은 단위 테스트와 별도로 golden case 기반 평가를 둔다.
구체적인 데이터셋, 실행 모드, baseline 정책은
[06. Evaluation](06-evaluation.md)을 따른다.

- intent: `primary_task`, `sub_intent`, `answer_strategy`가 기대값과 맞는지 검증
- routing: 선택된 answer agent가 기대값과 맞는지 검증
- retrieval: 재료 coverage, allergy exclusion, target title match를 검증
- consistency: 답변 텍스트가 `recipes` 이벤트 payload와 충돌하지 않는지 검증
- safety: 안전 민감 질문에서 위험한 단정 표현을 쓰지 않는지 검증
- latency: intent, planner, retrieval, verification, 최종 `message` 이벤트까지
  걸린 시간을 기록

## Example Cases

| Input | Expected Primary Task |
| --- | --- |
| `김치랑 있는 거 뭐 먹어?` | `RECIPE_FIND` |
| `새우 알레르기 저장해줘` | `PROFILE_MANAGEMENT` |
| `새우 알레르기 있는데 뭐 먹지?` | `RECIPE_FIND` + allergy constraint |
| `너는 누구야?` | `IDENTITY` |
| `비트코인 시세 알려줘` | `OFF_TOPIC` |
| `파 없으면 뭐로 대체해?` | `COOKING_QA` |

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
