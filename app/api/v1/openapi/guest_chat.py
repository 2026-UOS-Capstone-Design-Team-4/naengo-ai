from app.api.v1.openapi.errors import INTERNAL_ERROR_RESPONSE

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
                        "event: recipes\n"
                        'data: [{"id": 1, "title": "김치두부찌개"}]\n\n'
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
