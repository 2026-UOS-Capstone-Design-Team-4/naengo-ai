import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_id
from app.api.v1.docs.chat import (
    CHAT_NEW_ROOM_DESCRIPTION,
    CHAT_NEW_ROOM_SUMMARY,
    CHAT_RESPONSES,
    CHAT_ROOM_DESCRIPTION,
    CHAT_ROOM_SUMMARY,
    DELETE_ROOM_DESCRIPTION,
    DELETE_ROOM_RESPONSES,
    DELETE_ROOM_SUMMARY,
    GET_ROOM_MESSAGES_DESCRIPTION,
    GET_ROOM_MESSAGES_RESPONSES,
    GET_ROOM_MESSAGES_SUMMARY,
    GET_ROOMS_DESCRIPTION,
    GET_ROOMS_RESPONSES,
    GET_ROOMS_SUMMARY,
)
from app.db.session import get_db
from app.schemas.chat import ChatMessageResponse, ChatRequest, ChatRoomResponse
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/rooms",
    summary=GET_ROOMS_SUMMARY,
    description=GET_ROOMS_DESCRIPTION,
    response_model=list[ChatRoomResponse],
    responses=GET_ROOMS_RESPONSES,
)
async def get_rooms(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return ChatService(db).get_rooms(current_user_id)


@router.get(
    "/rooms/{room_id}",
    summary=GET_ROOM_MESSAGES_SUMMARY,
    description=GET_ROOM_MESSAGES_DESCRIPTION,
    response_model=list[ChatMessageResponse],
    responses=GET_ROOM_MESSAGES_RESPONSES,
)
async def get_room_messages(
    room_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    chat_service = ChatService(db)
    if not chat_service.get_room(room_id, current_user_id):
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
    return chat_service.get_room_messages(room_id)


@router.delete(
    "/rooms/{room_id}",
    summary=DELETE_ROOM_SUMMARY,
    description=DELETE_ROOM_DESCRIPTION,
    responses=DELETE_ROOM_RESPONSES,
)
async def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if not ChatService(db).delete_room(room_id, current_user_id):
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
    return {"message": "채팅방이 삭제되었습니다."}


@router.post(
    "/rooms",
    summary=CHAT_NEW_ROOM_SUMMARY,
    description=CHAT_NEW_ROOM_DESCRIPTION,
    response_class=StreamingResponse,
    responses=CHAT_RESPONSES,
)
async def create_room_and_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        chat_service = ChatService(db)
        room = chat_service.create_room(current_user_id, request.prompt)
        agent_service = AgentService()

        async def generate():
            data = json.dumps({"room_id": room.room_id})
            yield f"event: room\ndata: {data}\n\n"
            async for chunk in await agent_service.stream(
                prompt=request.prompt,
                image=request.image,
                room_id=room.room_id,
                history=[],
                user_id=current_user_id,
                chat_service=chat_service,
                db=db,
            ):
                yield chunk

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as exc:
        logger.error("create_room_and_chat 오류: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/rooms/{room_id}",
    summary=CHAT_ROOM_SUMMARY,
    description=CHAT_ROOM_DESCRIPTION,
    response_class=StreamingResponse,
    responses=CHAT_RESPONSES,
)
async def chat_in_room(
    room_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        chat_service = ChatService(db)
        if not chat_service.get_room(room_id, current_user_id):
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

        history = chat_service.load_recent_history(room_id, limit=10)
        agent_service = AgentService()

        return StreamingResponse(
            await agent_service.stream(
                prompt=request.prompt,
                image=request.image,
                room_id=room_id,
                history=history,
                user_id=current_user_id,
                chat_service=chat_service,
                db=db,
            ),
            media_type="text/event-stream",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("chat_in_room 오류: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
