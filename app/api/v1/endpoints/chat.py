import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import (
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy.orm import Session

from app.agents.dependencies import RecipeDeps
from app.agents.recipe_agent import recipe_agent
from app.api.v1.docs.chat import (
    CHAT_NEW_ROOM_DESCRIPTION,
    CHAT_NEW_ROOM_SUMMARY,
    CHAT_RESPONSES,
    CHAT_ROOM_DESCRIPTION,
    CHAT_ROOM_SUMMARY,
    GET_ROOM_MESSAGES_DESCRIPTION,
    GET_ROOM_MESSAGES_RESPONSES,
    GET_ROOM_MESSAGES_SUMMARY,
    GET_ROOMS_DESCRIPTION,
    GET_ROOMS_RESPONSES,
    GET_ROOMS_SUMMARY,
)
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatRoom
from app.models.recipe import Recipe
from app.schemas.chat import ChatMessageResponse, ChatRequest, ChatRoomResponse
from app.schemas.recipe import RecipeResponse

router = APIRouter()
logger = logging.getLogger(__name__)

TEMP_USER_ID = 1  # 인증 구현 전 임시 사용자

IDENTITY_PATTERNS = re.compile(
    r"(넌\s*누구|너\s*누구|네\s*이름|너의\s*이름|당신\s*누구|이름이\s*뭐|어떤\s*ai|무슨\s*ai|어느\s*회사|어떤\s*모델"
    r"|너는\s*뭐|넌\s*뭐|당신은\s*뭐|뭐\s*하는\s*(?:ai|프로그램|봇|것|거)"
    r"|who\s*are\s*you|what\s*are\s*you|your\s*name|what'?s\s*your\s*name"
    r"|gpt|chatgpt|claude|gemini|openai|google|anthropic)",
    re.IGNORECASE,
)
IDENTITY_RESPONSE = "저는 냉고예요! 냉장고 속 재료로 레시피를 추천해드리는 요리 전문가랍니다. 😊 어떤 재료가 있으신가요?"


def load_history(db: Session, room_id: int) -> list[ModelMessage]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    result = []
    for msg in messages:
        if msg.role == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
        else:
            result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
    return result


def save_messages(
    db: Session,
    room_id: int,
    user_content: str,
    ai_content: str,
    recipe_ids: list[int] | None = None,
):
    db.add(ChatMessage(room_id=room_id, role="user", content=user_content))
    db.add(ChatMessage(room_id=room_id, role="model", content=ai_content, recipe_ids=recipe_ids))
    db.commit()


async def run_chat_stream(
    request: ChatRequest,
    room_id: int,
    message_history: list[ModelMessage],
    db: Session,
):
    if IDENTITY_PATTERNS.search(request.prompt):

        async def identity_generator():
            data = json.dumps({"content": IDENTITY_RESPONSE}, ensure_ascii=False)
            yield f"event: message\ndata: {data}\n\n"
            save_messages(db, room_id, request.prompt, IDENTITY_RESPONSE)

        return StreamingResponse(identity_generator(), media_type="text/event-stream")

    user_prompt = (
        [request.prompt, ImageUrl(url=request.image)]
        if request.image
        else request.prompt
    )

    deps = RecipeDeps()

    async def event_generator():
        ai_full_response = ""

        async with recipe_agent.run_stream(
            user_prompt, message_history=message_history, deps=deps
        ) as result:
            async for chunk in result.stream_text(delta=True):
                ai_full_response += chunk
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"event: message\ndata: {data}\n\n"

        unique_recipes = (
            list({r["id"]: r for r in deps.last_found_recipes}.values())
            if deps.last_found_recipes
            else []
        )
        recipe_ids = [r["id"] for r in unique_recipes] if unique_recipes else None
        save_messages(db, room_id, request.prompt, ai_full_response, recipe_ids)

        if unique_recipes:
            data = json.dumps(unique_recipes, ensure_ascii=False)
            logger.info(
                f"💾 [Stream] {len(unique_recipes)}개의 레시피 데이터를 전송합니다."
            )
            yield f"event: recipes\ndata: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/rooms",
    summary=GET_ROOMS_SUMMARY,
    description=GET_ROOMS_DESCRIPTION,
    response_model=list[ChatRoomResponse],
    responses=GET_ROOMS_RESPONSES,
)
async def get_rooms(db: Session = Depends(get_db)):
    rooms = (
        db.query(ChatRoom)
        .filter(ChatRoom.user_id == TEMP_USER_ID)
        .order_by(ChatRoom.updated_at.desc())
        .all()
    )
    return rooms


@router.get(
    "/rooms/{room_id}",
    summary=GET_ROOM_MESSAGES_SUMMARY,
    description=GET_ROOM_MESSAGES_DESCRIPTION,
    response_model=list[ChatMessageResponse],
    responses=GET_ROOM_MESSAGES_RESPONSES,
)
async def get_room_messages(room_id: int, db: Session = Depends(get_db)):
    room = (
        db.query(ChatRoom)
        .filter(ChatRoom.room_id == room_id, ChatRoom.user_id == TEMP_USER_ID)
        .first()
    )
    if not room:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    result = []
    for msg in messages:
        recipes = None
        if msg.recipe_ids:
            recipe_rows = (
                db.query(Recipe)
                .filter(Recipe.recipe_id.in_(msg.recipe_ids), Recipe.is_active == True)  # noqa: E712
                .all()
            )
            recipes = [RecipeResponse.model_validate(r) for r in recipe_rows]
        result.append(
            ChatMessageResponse(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                recipes=recipes,
                created_at=msg.created_at,
            )
        )
    return result


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
):
    try:
        title = request.prompt[:100] if len(request.prompt) > 100 else request.prompt
        room = ChatRoom(user_id=TEMP_USER_ID, title=title)
        db.add(room)
        db.commit()
        db.refresh(room)

        async def with_room_event():
            data = json.dumps({"room_id": room.room_id})
            yield f"event: room\ndata: {data}\n\n"
            response = await run_chat_stream(request, room.room_id, [], db)
            async for chunk in response.body_iterator:
                yield chunk

        return StreamingResponse(with_room_event(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in create_room_and_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
):
    try:
        room = (
            db.query(ChatRoom)
            .filter(
                ChatRoom.room_id == room_id,
                ChatRoom.user_id == TEMP_USER_ID,
            )
            .first()
        )
        if not room:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

        MAX_HISTORY = 10
        all_history = load_history(db, room_id)
        message_history = all_history[-MAX_HISTORY:]

        return await run_chat_stream(request, room_id, message_history, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_in_room: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
