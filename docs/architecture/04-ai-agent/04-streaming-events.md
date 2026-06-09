# 04. Streaming Events

AI 채팅 응답은 SSE로 스트리밍한다.

## Events

| Event | Data | Purpose |
| --- | --- | --- |
| `room` | `{ "room_id": number }` | 새 채팅방 ID 전달 (`POST /rooms` 전용) |
| `metadata` | `{ "primary_task": string, "model": string, "used_live_research": boolean, "source_count": number }` | 스트림 메타데이터 |
| `planning` | `{ "primary_task": string, "sub_intent": string?, "answer_strategy": string, "planner": string?, "selected_agent": string?, "confidence": number }` | task/planner/sub-intent/선택 agent |
| `workflow` | `{ "run_id": string, "stage": string, "status": string, "attempt": number }` | 요청 단계와 검증/수정 진행 상태 |
| `context` | `{ "resolved_recipe_id": number, "title": string }` | 최근 추천 등 참조 해석 결과 |
| `retrieval` | `{ "status": "started" \| "completed" \| "failed", "candidate_count": number?, "selected_count": number? }` | RAG 검색 진행/결과 |
| `evidence` | `{ "recipes": EvidenceRecipe[], "constraints": object }` | 추천 근거 요약과 사용자 검색 조건 |
| `message` | `{ "content": string }` | AI 답변 chunk |
| `profile_update` | `{ "action": string, "candidates": ProfileUpdateCandidate[] }` | 프로필 저장/확인 결과 |
| `recipes` | `Recipe[]` | 추천 레시피 목록 |
| `done` | `{ "message_id": number \| null, "recipe_ids": number[] }` | 스트림 종료 |
| `error` | `{ "code": string, "message": string }` | 스트림 중 오류 |

## Rules

- `room`은 `POST /rooms`(새 방 생성)에서만 전송한다. 기존 방 메시지(`POST /rooms/{room_id}`)에서는 보내지 않는다.
- `workflow.stage`는 `classifying`, `planning`, `retrieving`, `generating`,
  `verifying`, `revising`, `completed`, `failed` 중 하나다.
- `workflow.status`는 `started`, `completed`, `skipped`, `failed` 중 하나다.
  `attempt=0`은 최초 생성/검증, `attempt=1`은 수정 단계다.
- `run_id`는 요청 단위 UUID이며 메모리에서만 사용하고 DB에 저장하지 않는다.
- `message`는 검증과 필요 시 1회 수정을 마친 최종 텍스트를 한 번 전송한다.
- `planning`은 응답 생성 전에 현재 task, sub intent, answer strategy, 선택된 answer agent를 알려준다.
- `context`는 "첫 번째로 추천한 김치두부찌개"처럼 이전 추천을 가리키는 참조가
  실제 레시피로 해석된 경우에만 보낸다.
- `retrieval`은 RAG 검색이 수행된 경우에만 보내며, 긴 검색 UI를 위해 시작과
  완료/실패 상태를 구분할 수 있다.
- `evidence`는 RAG 검색이 완료되고 근거 또는 검색 조건이 있는 경우에만 보낸다.
  프론트에서 추천 이유, 제외 조건, 시간 제한 같은 설명 UI에 사용한다.
- `profile_update`는 `AUTO_SAVE`, `REQUIRE_CONFIRMATION` 결과만 보낸다. `IGNORE`는 전송하지 않는다.
- `recipes`는 중복 제거된 최종 추천 목록만 보낸다.
- `done`은 스트림의 terminal event다. 로그인 채팅은 DB 저장 완료 후
  `message_id`를 포함하고, 게스트 채팅이나 저장되지 않은 종료는
  `message_id=null`을 보낸다.
- 예외 발생 시 가능한 경우 `error` 이벤트를 보내고, 클라이언트 종료 처리를
  단순하게 하기 위해 terminal `done` 이벤트로 닫는다.

## Profile Update Event

`PROFILE_MANAGEMENT` task 또는 로그인 사용자의 요리 관련 턴에서 자동 저장했거나
사용자 확인이 필요한 후보가 있으면 `profile_update` 이벤트를 보낼 수 있다.

자동 저장 예:

```json
{
  "action": "AUTO_SAVE",
  "candidates": [
    {
      "field": "allergies",
      "operation": "add",
      "value": "새우",
      "confidence": 0.96
    }
  ]
}
```

확인 필요 예:

```json
{
  "action": "REQUIRE_CONFIRMATION",
  "candidates": [
    {
      "field": "dietary_restrictions",
      "operation": "add",
      "value": "저탄수화물",
      "confidence": 0.72,
      "reason": "건강 상태와 연결된 식단 정보라 사용자 확인이 필요함"
    }
  ]
}
```

프로필 변경은 `message` 텍스트에도 짧게 포함해 사용자가 저장 사실을 놓치지 않게 한다.

## Frontend Benefit

- 스트림 종료 판단이 쉬워진다.
- 오류 UI를 명확히 표시할 수 있다.
- intent 기반 UI 분기가 가능해진다.
