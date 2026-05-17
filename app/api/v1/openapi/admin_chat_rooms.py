from app.api.v1.openapi.errors import (
    FORBIDDEN_RESPONSE,
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)

ADMIN_CHAT_ROOM_NOT_FOUND_RESPONSE = error_response(
    "관리자 채팅방을 찾을 수 없습니다.",
    "CHAT_ROOM_NOT_FOUND",
    "Chat room was not found.",
)

DELETE_ADMIN_CHAT_ROOM_SUMMARY = "[관리자] 채팅방 완전 삭제"
DELETE_ADMIN_CHAT_ROOM_OPERATION_ID = "deleteAdminChatRoom"
DELETE_ADMIN_CHAT_ROOM_ID_DESCRIPTION = "완전히 삭제할 채팅방 ID입니다."
DELETE_ADMIN_CHAT_ROOM_DESCRIPTION = r"""
관리자 권한으로 채팅방과 해당 채팅방의 메시지를 DB에서 완전히 삭제합니다.

- 일반 사용자 채팅방 삭제와 달리 `is_active`만 변경하지 않습니다.
- 삭제된 채팅방은 복구할 수 없으므로 운영 관리 화면에서 신중하게 호출해야 합니다.
- 존재하지 않는 채팅방이면 `404 CHAT_ROOM_NOT_FOUND`를 반환합니다.
"""

DELETE_ADMIN_CHAT_ROOM_RESPONSES = {
    204: {
        "description": "채팅방과 메시지를 완전히 삭제했습니다.",
    },
    401: UNAUTHENTICATED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    404: ADMIN_CHAT_ROOM_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}
