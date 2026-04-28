from app.api.v1.docs.examples import (
    CHAT_MESSAGE_MODEL_EXAMPLE,
    CHAT_MESSAGE_USER_EXAMPLE,
    CHAT_ROOM_EXAMPLE,
    RECIPE_EXAMPLE,
)

_RECIPE_RESPONSE_TABLE = r"""
**RecipeResponse 데이터 구조**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | int | 레시피 ID |
| `title` | string | 레시피 제목 |
| `description` | string | 레시피 설명 |
| `ingredients` | IngredientItem[] | 재료 목록 |
| `ingredients_raw` | string | 재료 원문 텍스트 |
| `instructions` | string[] | 조리 순서 |
| `servings` | float | 인분 수 |
| `cooking_time` | int | 조리 시간 (분) |
| `calories` | int \| null | 칼로리 (kcal) |
| `difficulty` | string | 난이도 (`easy` / `normal` / `hard`) |
| `category` | string[] | 카테고리 |
| `tags` | string[] | 태그 |
| `tips` | string[] | 조리 팁 |
| `video_url` | string \| null | YouTube 영상 URL |
| `image_url` | string \| null | 이미지 URL |
| `author_type` | string | 작성자 유형 (`ADMIN` / `USER`) |

**IngredientItem 데이터 구조**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 재료명 |
| `amount` | string | 양 |
| `unit` | string | 단위 |
| `type` | string | 종류 (메인 / 부재료 등) |
| `note` | string \| null | 비고 |
"""

_COMMON_SSE_DESCRIPTION = r"""
- **응답 방식**: `text/event-stream` 형식으로 이벤트를 실시간 전송합니다.
- **message 이벤트**: AI 텍스트 청크를 `{"content": "..."}` 형식으로 스트리밍합니다.
- **recipes 이벤트**: 답변 완료 후 검색된 레시피 목록을 `RecipeResponse[]` 형식으로 전송합니다. 레시피가 없으면 전송하지 않습니다.
- **이미지**: `image`에 base64 data URL(`data:image/jpeg;base64,...`)을 포함하면 멀티모달로 동작합니다.
""" + _RECIPE_RESPONSE_TABLE

# ── GET /rooms ────────────────────────────────────────────────────────────────

GET_ROOMS_SUMMARY = "채팅방 목록 조회"
GET_ROOMS_DESCRIPTION = r"""
사용자의 채팅방 목록을 `updated_at` 내림차순으로 반환합니다.

**응답 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `room_id` | int | 채팅방 ID |
| `title` | string | 채팅방 제목 (첫 질문 내용) |
| `created_at` | datetime | 생성 시각 |
| `updated_at` | datetime | 마지막 수정 시각 |
"""

GET_ROOMS_RESPONSES = {
    200: {
        "description": "채팅방 목록",
        "content": {
            "application/json": {
                "example": [
                    CHAT_ROOM_EXAMPLE,
                    {
                        "room_id": 2,
                        "title": "계란이랑 양배추로 만들 수 있는 거 알려줘",
                        "created_at": "2026-04-28T10:00:00+09:00",
                        "updated_at": "2026-04-28T10:03:00+09:00",
                    },
                ]
            }
        },
    }
}

# ── GET /rooms/{room_id} ──────────────────────────────────────────────────────

GET_ROOM_MESSAGES_SUMMARY = "채팅 내역 조회"
GET_ROOM_MESSAGES_DESCRIPTION = r"""
채팅방의 전체 메시지를 시간순으로 반환합니다.
`role = model`인 메시지에 레시피가 있었다면 `recipes` 필드에 전체 레시피 데이터를 포함합니다.

**응답 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `message_id` | int | 메시지 ID |
| `role` | string | 발화자 (`user` / `model`) |
| `content` | string | 메시지 내용 |
| `recipes` | RecipeResponse[] \| null | 추천 레시피 목록 (없으면 null) |
| `created_at` | datetime | 생성 시각 |
""" + _RECIPE_RESPONSE_TABLE

GET_ROOM_MESSAGES_RESPONSES = {
    200: {
        "description": "시간순 메시지 목록",
        "content": {
            "application/json": {
                "example": [CHAT_MESSAGE_USER_EXAMPLE, CHAT_MESSAGE_MODEL_EXAMPLE]
            }
        },
    },
    404: {"description": "채팅방을 찾을 수 없습니다."},
}

# ── POST /rooms ───────────────────────────────────────────────────────────────

CHAT_NEW_ROOM_SUMMARY = "새 채팅방 생성 및 첫 메시지 전송 (SSE)"
CHAT_NEW_ROOM_DESCRIPTION = r"""
새 채팅방을 생성하고 첫 메시지를 전송합니다. 채팅방 제목은 첫 질문 내용으로 자동 설정됩니다.

- **room 이벤트**: 스트림 시작 시 생성된 채팅방 ID를 `{"room_id": 1}` 형식으로 전송합니다.
""" + _COMMON_SSE_DESCRIPTION

# ── POST /rooms/{room_id} ─────────────────────────────────────────────────────

CHAT_ROOM_SUMMARY = "기존 채팅방에서 메시지 전송 (SSE)"
CHAT_ROOM_DESCRIPTION = r"""
기존 채팅방에서 메시지를 전송합니다. 최근 10개의 대화 이력을 자동으로 불러와 컨텍스트로 사용합니다.
""" + _COMMON_SSE_DESCRIPTION

# ── 공통 SSE 응답 예시 ─────────────────────────────────────────────────────────

CHAT_RESPONSES = {
    200: {
        "description": "SSE 형식의 실시간 스트림 응답",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": (
                        "event: room\n"
                        'data: {"room_id": 1}\n\n'
                        "event: message\n"
                        'data: {"content": "김치"}\n\n'
                        "event: message\n"
                        'data: {"content": "와 두부로 만들 수 있는 레시피를 찾았어요!"}\n\n'
                        "event: recipes\n"
                        "data: ["
                        '{"id": 1, "title": "김치두부찌개", "description": "칼칼하고 깊은 맛의 찌개입니다.", '
                        '"ingredients": [{"name": "김치", "amount": "200", "unit": "g", "type": "메인", "note": "잘 익은 것"}], '
                        '"ingredients_raw": "김치 200g, 두부 1모", '
                        '"instructions": ["냄비에 기름을 두르고 김치를 볶는다.", "물을 붓고 끓어오르면 두부를 넣는다."], '
                        '"servings": 2.0, "cooking_time": 20, "calories": 180, "difficulty": "easy", '
                        '"category": ["한식", "찌개"], "tags": ["얼큰한", "국물요리"], '
                        '"tips": ["김치는 충분히 익은 것을 사용해야 맛이 좋습니다."], '
                        '"video_url": "https://youtube.com/watch?v=example", '
                        '"image_url": "https://example.com/image.jpg", "author_type": "ADMIN"}'
                        "]\n\n"
                    ),
                }
            }
        },
    },
    404: {"description": "채팅방을 찾을 수 없습니다."},
}
