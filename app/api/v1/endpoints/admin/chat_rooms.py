from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.openapi.admin_chat_rooms import (
    DELETE_ADMIN_CHAT_ROOM_DESCRIPTION,
    DELETE_ADMIN_CHAT_ROOM_ID_DESCRIPTION,
    DELETE_ADMIN_CHAT_ROOM_OPERATION_ID,
    DELETE_ADMIN_CHAT_ROOM_RESPONSES,
    DELETE_ADMIN_CHAT_ROOM_SUMMARY,
)
from app.db.session import get_db
from app.services.admin_chat_room_service import (
    AdminChatRoomNotFoundError,
    AdminChatRoomService,
)

router = APIRouter()


@router.delete(
    "/{room_id}",
    summary=DELETE_ADMIN_CHAT_ROOM_SUMMARY,
    description=DELETE_ADMIN_CHAT_ROOM_DESCRIPTION,
    operation_id=DELETE_ADMIN_CHAT_ROOM_OPERATION_ID,
    status_code=status.HTTP_204_NO_CONTENT,
    responses=DELETE_ADMIN_CHAT_ROOM_RESPONSES,
)
def hard_delete_admin_chat_room(
    room_id: int = Path(description=DELETE_ADMIN_CHAT_ROOM_ID_DESCRIPTION, ge=1),
    db: Session = Depends(get_db),
) -> Response:
    try:
        AdminChatRoomService(db).hard_delete_room(room_id)
    except AdminChatRoomNotFoundError:
        raise ApiError(
            404,
            "CHAT_ROOM_NOT_FOUND",
            "Chat room was not found.",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
