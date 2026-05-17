from app.api.v1.openapi.errors import INTERNAL_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import (
    CHAT_MESSAGE_MODEL_EXAMPLE,
    CHAT_MESSAGE_USER_EXAMPLE,
    CHAT_ROOM_EXAMPLE,
)

CHAT_ROOM_NOT_FOUND_RESPONSE = error_response(
    "채팅방을 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "채팅방을 찾을 수 없습니다.",
)

_RECIPE_RESPONSE_TABLE = r"""
**RecipeResponse 구조**

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | int | 레시피 ID |
| `title` | string | 레시피 제목 |
| `description` | string | 레시피 설명 |
| `ingredients` | IngredientItem[] | 재료 목록 |
| `ingredients_raw` | string | 재료 원문 텍스트 |
| `steps` | RecipeStepResponse[] | 조리 단계 목록 |
| `servings` | float | 인분 수 |
| `cooking_time_minutes` | int | 조리 시간(분) |
| `kcal_per_serving` | int \| null | 1인분당 kcal |
| `difficulty` | string | 난이도(`easy` / `normal` / `hard`) |
| `category` | string[] | 카테고리 |
| `tags` | string[] | 태그 |
| `tips` | string[] | 조리 팁 |
| `video_url` | string \| null | 영상 URL |
| `image_url` | string \| null | 이미지 URL |
| `author_type` | string | 작성자 유형(`ADMIN` / `USER` / `SOURCE`) |
"""

_COMMON_SSE_DESCRIPTION = (
    r"""
- **응답 방식**: `text/event-stream` 형식으로 이벤트를 실시간 전송합니다.
- **metadata 이벤트**: intent, live research 사용 여부, source count 등 실행 정보를 전송합니다.
- **message 이벤트**: AI 텍스트 조각을 `{"content": "..."}` 형식으로 전송합니다.
- **profile_update 이벤트**: agent가 사용자 프로필 후보를 저장/확인/무시한 결과를 전송합니다.
- **recipes 이벤트**: 응답 완료 후 검색된 레시피 목록을 `RecipeResponse[]`로 전송합니다.
- **done 이벤트**: 스트림 종료를 알립니다.
- **error 이벤트**: 처리 중 오류가 발생하면 표준 에러 payload를 전송합니다.
- **이미지**: `image`에 base64 data URL을 넣으면 멀티모달 입력으로 처리합니다.
"""
    + _RECIPE_RESPONSE_TABLE
)

GET_ROOMS_SUMMARY = "채팅방 목록 조회"
GET_ROOMS_DESCRIPTION = r"""
현재 사용자의 활성 채팅방 목록을 `updated_at` 내림차순으로 반환합니다.

삭제 처리된 채팅방(`is_active = false`)은 목록에서 제외합니다.
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
                        "title": "계란이랑 배추로 만들 수 있는 야식 알려줘",
                        "created_at": "2026-04-28T10:00:00+09:00",
                        "updated_at": "2026-04-28T10:03:00+09:00",
                    },
                ]
            }
        },
    }
}

GET_ROOM_MESSAGES_SUMMARY = "채팅 이력 조회"
GET_ROOM_MESSAGES_DESCRIPTION = (
    r"""
채팅방의 전체 메시지를 시간순으로 반환합니다.

`role = model` 메시지에 추천 레시피가 연결되어 있으면 `recipes` 필드에
전체 레시피 데이터를 포함합니다.
"""
    + _RECIPE_RESPONSE_TABLE
)

GET_ROOM_MESSAGES_RESPONSES = {
    200: {
        "description": "시간순 메시지 목록",
        "content": {
            "application/json": {
                "example": [CHAT_MESSAGE_USER_EXAMPLE, CHAT_MESSAGE_MODEL_EXAMPLE]
            }
        },
    },
    404: CHAT_ROOM_NOT_FOUND_RESPONSE,
}

DELETE_ROOM_SUMMARY = "채팅방 삭제"
DELETE_ROOM_DESCRIPTION = r"""
채팅방을 숨김 처리합니다.

- 실제 데이터는 삭제하지 않고 `is_active`를 `false`로 변경합니다.
- 삭제된 채팅방은 `GET /rooms`에서 제외합니다.
- 이미 삭제된 채팅방에 요청하면 `404 RESOURCE_NOT_FOUND`를 반환합니다.
"""

DELETE_ROOM_RESPONSES = {
    200: {
        "description": "삭제 성공",
        "content": {
            "application/json": {"example": {"message": "채팅방이 삭제되었습니다."}}
        },
    },
    404: CHAT_ROOM_NOT_FOUND_RESPONSE,
}

CHAT_NEW_ROOM_SUMMARY = "새 채팅방 생성 및 첫 메시지 전송 (SSE)"
CHAT_NEW_ROOM_DESCRIPTION = (
    r"""
새 채팅방을 생성하고 첫 메시지를 전송합니다.
채팅방 제목은 첫 질문 내용으로 자동 설정합니다.

- **room 이벤트**: 스트림 시작 때 생성된 채팅방 ID를 전송합니다.
"""
    + _COMMON_SSE_DESCRIPTION
)

CHAT_ROOM_SUMMARY = "기존 채팅방에 메시지 전송 (SSE)"
CHAT_ROOM_DESCRIPTION = (
    r"""
기존 채팅방에 메시지를 전송합니다.
최근 10개의 대화 이력을 자동으로 불러와 AI 컨텍스트로 사용합니다.
"""
    + _COMMON_SSE_DESCRIPTION
)

CHAT_RESPONSES = {
    200: {
        "description": "SSE 형식의 실시간 스트리밍 응답",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": (
                        "event: room\n"
                        'data: {"room_id": 1}\n\n'
                        "event: metadata\n"
                        'data: {"intent_type":"RECIPE_RECOMMENDATION","model":"gpt-5.4-mini","used_live_research":false,"source_count":0}\n\n'
                        "event: message\n"
                        'data: {"content": "김치와 두부로 만들 수 있는 레시피를 찾아볼게요."}\n\n'
                        "event: profile_update\n"
                        'data: {"action":"ignored","candidates":[]}\n\n'
                        "event: recipes\n"
                        'data: [{"id": 1, "title": "김치두부찌개"}]\n\n'
                        "event: done\n"
                        "data: {}\n\n"
                    ),
                }
            }
        },
    },
    404: CHAT_ROOM_NOT_FOUND_RESPONSE,
    500: INTERNAL_ERROR_RESPONSE,
}
