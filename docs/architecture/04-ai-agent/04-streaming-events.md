# 04. Streaming Events

AI 채팅 응답은 SSE로 스트리밍한다.

## Events

| Event | Data | Purpose |
| --- | --- | --- |
| `room` | `{ "room_id": number }` | 새 채팅방 ID 전달 (`POST /rooms` 전용) |
| `metadata` | `{ "intent_type": string, "model": string, "used_live_research": boolean, "source_count": number }` | 스트림 메타데이터 |
| `message` | `{ "content": string }` | AI 답변 chunk |
| `profile_update` | `{ "action": string, "candidates": ProfileUpdateCandidate[] }` | 프로필 저장/확인 결과 |
| `recipes` | `Recipe[]` | 추천 레시피 목록 |
| `done` | `{ "message_id": number, "recipe_ids": number[] }` | 정상 종료 |
| `error` | `{ "code": string, "message": string }` | 스트림 중 오류 |

## Rules

- `room`은 `POST /rooms`(새 방 생성)에서만 전송한다. 기존 방 메시지(`POST /rooms/{room_id}`)에서는 보내지 않는다.
- `message`는 순수 텍스트 delta만 보낸다.
- `profile_update`는 `AUTO_SAVE`, `REQUIRE_CONFIRMATION` 결과만 보낸다. `IGNORE`는 전송하지 않는다.
- `recipes`는 중복 제거된 최종 추천 목록만 보낸다.
- `done`은 DB 저장 완료 후 보낸다.
- 예외 발생 시 가능한 경우 `error` 이벤트를 보내고 스트림을 닫는다.

## Profile Update Event

`PROFILE_UPDATE` route에서 자동 저장했거나 사용자 확인이 필요한 후보가 있으면 `profile_update` 이벤트를 보낼 수 있다.

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
