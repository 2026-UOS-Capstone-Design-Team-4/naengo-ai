# 04. Streaming Events

AI 채팅 응답은 SSE로 스트리밍한다.

## Current Events

| Event | Data |
| --- | --- |
| `room` | `{ "room_id": number }` |
| `message` | `{ "content": string }` |
| `recipes` | `Recipe[]` |

## Target Events

| Event | Data | Purpose |
| --- | --- | --- |
| `room` | `{ "room_id": number }` | 새 채팅방 ID 전달 |
| `metadata` | `{ "intent_type": string, "model": string }` | 스트림 메타데이터 |
| `message` | `{ "content": string }` | AI 답변 chunk |
| `recipes` | `Recipe[]` | 추천 레시피 목록 |
| `done` | `{ "message_id": number, "recipe_ids": number[] }` | 정상 종료 |
| `error` | `{ "code": string, "message": string }` | 스트림 중 오류 |

## Rules

- `message`는 순수 텍스트 delta만 보낸다.
- `recipes`는 중복 제거된 최종 추천 목록만 보낸다.
- `done`은 DB 저장 완료 후 보낸다.
- 예외 발생 시 가능한 경우 `error` 이벤트를 보내고 스트림을 닫는다.

## Frontend Benefit

- 스트림 종료 판단이 쉬워진다.
- 오류 UI를 명확히 표시할 수 있다.
- intent 기반 UI 분기가 가능해진다.
