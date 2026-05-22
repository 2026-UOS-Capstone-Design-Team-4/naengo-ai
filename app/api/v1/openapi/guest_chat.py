import json

from app.api.v1.openapi.errors import INTERNAL_ERROR_RESPONSE
from app.api.v1.openapi.examples import RECIPE_EXAMPLE, RECIPE_RESPONSE_TABLE

_RECIPES_EVENT_DATA = json.dumps([RECIPE_EXAMPLE], ensure_ascii=False)

GUEST_CHAT_DESCRIPTION = (
    r"""
비로그인 사용자를 위한 AI 레시피 추천 채팅입니다.

대화 기록(`history`)은 클라이언트가 직접 관리하며 요청마다 전달합니다.
서버에는 메시지가 저장되지 않습니다.
`history`는 최대 20개(10턴)까지 허용되며, 초과 시 422를 반환합니다.

- **응답 방식**: `text/event-stream` 형식으로 이벤트를 실시간 전송합니다.
- **metadata 이벤트**: intent 분류 결과, live research 사용 여부, source count를 전송합니다.
- **message 이벤트**: AI 텍스트 조각을 `{"content": "..."}` 형식으로 여러 번 전송합니다.
- **recipes 이벤트**: 레시피 추천 흐름에서 응답 완료 후 검색된 레시피 목록을 `RecipeResponse[]`로 전송합니다.
- **done 이벤트**: 스트림 종료를 알립니다. `message_id`는 저장이 없으므로 항상 `null`입니다.
- **error 이벤트**: 처리 중 오류가 발생하면 표준 에러 payload를 전송합니다.
- **이미지**: `image`에 base64 data URL을 넣으면 멀티모달 입력으로 처리합니다.
"""
    + RECIPE_RESPONSE_TABLE
    + "\n> `is_liked`, `is_scrapped`는 비로그인 상태이므로 항상 `false`입니다.\n"
)

GUEST_CHAT_RESPONSES = {
    200: {
        "description": "SSE 형식의 실시간 스트리밍 응답",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": (
                        "event: metadata\n"
                        'data: {"intent_type":"RECIPE_RECOMMENDATION","model":"gpt-5.4-mini","used_live_research":false,"source_count":0}\n\n'
                        "event: message\n"
                        'data: {"content": "김치와 두부로 만들 수 있는 레시피를 찾아볼게요."}\n\n'
                        "event: message\n"
                        'data: {"content": " 김치두부찌개를 추천드려요!"}\n\n'
                        "event: recipes\n"
                        f"data: {_RECIPES_EVENT_DATA}\n\n"
                        "event: done\n"
                        'data: {"message_id": null, "recipe_ids": [1]}\n\n'
                    ),
                }
            }
        },
    },
    422: {
        "description": "요청 값이 유효하지 않습니다. (이미지 크기 초과, history 20개 초과 등)",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": "Request validation failed.",
                        "details": {},
                    }
                }
            }
        },
    },
    500: INTERNAL_ERROR_RESPONSE,
}
