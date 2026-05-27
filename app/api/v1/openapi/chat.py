import json

from app.api.v1.openapi.errors import INTERNAL_ERROR_RESPONSE, error_response
from app.api.v1.openapi.examples import (
    CHAT_MESSAGE_MODEL_EXAMPLE,
    CHAT_MESSAGE_USER_EXAMPLE,
    CHAT_ROOM_EXAMPLE,
    RECIPE_EXAMPLE,
    RECIPE_RESPONSE_TABLE,
)

CHAT_ROOM_NOT_FOUND_RESPONSE = error_response(
    "채팅방을 찾을 수 없습니다.",
    "RESOURCE_NOT_FOUND",
    "채팅방을 찾을 수 없습니다.",
)

STORAGE_NOT_CONFIGURED_RESPONSE = error_response(
    "이미지 전송을 위한 스토리지가 설정되지 않았습니다.",
    "STORAGE_NOT_CONFIGURED",
    "이미지 전송을 위한 스토리지가 설정되지 않았습니다.",
)

CHAT_VALIDATION_RESPONSE = error_response(
    "요청 값이 유효하지 않습니다. (이미지 크기 초과 등)",
    "VALIDATION_FAILED",
    "Request validation failed.",
    {
        "fields": [
            {
                "name": "body.image",
                "reason": "Value error, 이미지 크기는 10MB를 초과할 수 없습니다.",
            }
        ]
    },
)

_COMMON_SSE_DESCRIPTION = (
    r"""
- **응답 방식**: `text/event-stream` 형식으로 이벤트를 실시간 전송합니다.
- **metadata 이벤트**: primary task, live research 사용 여부, source count를 전송합니다.
- **planning 이벤트**: planner, sub intent, answer strategy, 선택된 answer agent를 전송합니다.
- **context 이벤트**: 이전 추천 레시피를 이어 묻는 `COOKING_QA`에서 참조가 해석되면 `{"resolved_recipe_id": 1, "title": "김치두부찌개"}` 형식으로 전송합니다.
  예: "첫 번째로 추천한 김치두부찌개에서 돼지고기를 빼도 돼?"처럼 최근 추천 레시피를 이어 묻는 경우입니다.
- **retrieval 이벤트**: RAG 검색 상태(`started`, `completed`, `failed`)와 선택된 레시피 수를 전송합니다.
- **evidence 이벤트**: RAG 검색이 완료되면 추천 근거 요약과 사용자 검색 조건을 `{"recipes": [...], "constraints": {...}}` 형식으로 전송합니다.
- **message 이벤트**: AI 텍스트 조각을 `{"content": "..."}` 형식으로 여러 번 전송합니다.
- **profile_update 이벤트**: 프로필 관리 또는 요리 관련 흐름의 프로필 side effect에서 `AUTO_SAVE` 또는 `REQUIRE_CONFIRMATION` 결과만 포함되며, `IGNORE`는 전송하지 않습니다. 저장 안내는 일반 `message` 조각에도 포함될 수 있습니다.
- **recipes 이벤트**: 레시피 추천 흐름에서 응답 완료 후 검색된 레시피 목록을 `RecipeResponse[]`로 전송합니다.
- **done 이벤트**: 스트림 종료를 나타내는 terminal 이벤트입니다. `message_id`는 저장된 AI 메시지 ID이며, 저장 전 오류에서는 `null`일 수 있습니다.
- **error 이벤트**: 처리 중 오류가 발생하면 표준 에러 payload를 전송합니다. 가능한 경우 이후 terminal `done` 이벤트가 이어집니다.
- **이미지**: `image`에 base64 data URL을 넣으면 멀티모달 입력으로 처리합니다.
"""
    + RECIPE_RESPONSE_TABLE
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
    + RECIPE_RESPONSE_TABLE
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

_RECIPES_EVENT_DATA = json.dumps([RECIPE_EXAMPLE], ensure_ascii=False)
_EVIDENCE_EVENT_DATA = json.dumps(
    {
        "recipes": [
            {
                "recipe_id": 1,
                "title": "김치두부찌개",
                "why_matched": ["김치", "두부", "20분 이내"],
                "risk_flags": [],
                "missing_ingredients": [],
                "time_minutes": 20,
                "difficulty": "easy",
            }
        ],
        "constraints": {"avoid_ingredients": ["새우"], "max_time_minutes": 20},
    },
    ensure_ascii=False,
)

_COMMON_SSE_STREAM = (
    "event: metadata\n"
    'data: {"primary_task":"RECIPE_FIND","model":"gpt-5.4-mini","used_live_research":false,"source_count":0}\n\n'
    "event: planning\n"
    'data: {"primary_task":"RECIPE_FIND","sub_intent":"BY_INGREDIENTS","answer_strategy":"RECIPE_RECOMMENDATION","planner":"RecipeFindPlanner","selected_agent":"recipe_agent","confidence":0.92}\n\n'
    "event: retrieval\n"
    'data: {"status":"started"}\n\n'
    "event: retrieval\n"
    'data: {"status":"completed","candidate_count":1,"selected_count":1}\n\n'
    "event: evidence\n"
    f"data: {_EVIDENCE_EVENT_DATA}\n\n"
    "event: message\n"
    'data: {"content": "김치와 두부로 만들 수 있는 레시피를 찾아볼게요."}\n\n'
    "event: message\n"
    'data: {"content": " 김치두부찌개를 추천드려요!"}\n\n'
    "event: recipes\n"
    f"data: {_RECIPES_EVENT_DATA}\n\n"
    "event: done\n"
    'data: {"message_id": 42, "recipe_ids": [1]}\n\n'
)

CHAT_NEW_ROOM_RESPONSES = {
    200: {
        "description": "SSE 형식의 실시간 스트리밍 응답",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": ('event: room\ndata: {"room_id": 1}\n\n')
                    + _COMMON_SSE_STREAM,
                }
            }
        },
    },
    422: CHAT_VALIDATION_RESPONSE,
    503: STORAGE_NOT_CONFIGURED_RESPONSE,
    500: INTERNAL_ERROR_RESPONSE,
}

CHAT_ROOM_RESPONSES = {
    200: {
        "description": "SSE 형식의 실시간 스트리밍 응답",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "example": _COMMON_SSE_STREAM,
                }
            }
        },
    },
    404: CHAT_ROOM_NOT_FOUND_RESPONSE,
    422: CHAT_VALIDATION_RESPONSE,
    503: STORAGE_NOT_CONFIGURED_RESPONSE,
    500: INTERNAL_ERROR_RESPONSE,
}
