from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatRoom
from app.models.recipe import Recipe
from app.schemas.chat import ChatMessageResponse
from app.schemas.recipe import RecipeResponse


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def get_rooms(self, user_id: int) -> list[ChatRoom]:
        return (
            self.db.query(ChatRoom)
            .filter(
                ChatRoom.user_id == user_id,
                ChatRoom.is_active.is_(True),
            )
            .order_by(ChatRoom.updated_at.desc())
            .all()
        )

    def get_room(self, room_id: int, user_id: int) -> ChatRoom | None:
        return (
            self.db.query(ChatRoom)
            .filter(ChatRoom.room_id == room_id, ChatRoom.user_id == user_id)
            .first()
        )

    def get_active_room(self, room_id: int, user_id: int) -> ChatRoom | None:
        return (
            self.db.query(ChatRoom)
            .filter(
                ChatRoom.room_id == room_id,
                ChatRoom.user_id == user_id,
                ChatRoom.is_active.is_(True),
            )
            .first()
        )

    def create_room(self, user_id: int, prompt: str) -> ChatRoom:
        title = prompt[:100] if len(prompt) > 100 else prompt
        room = ChatRoom(user_id=user_id, title=title)
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def delete_room(self, room_id: int, user_id: int) -> bool:
        room = self.get_active_room(room_id, user_id)
        if not room:
            return False

        room.is_active = False
        self.db.commit()
        return True

    def get_room_messages(self, room_id: int) -> list[ChatMessageResponse]:
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        result = []
        for msg in messages:
            recipes = self._get_recipes(msg.recipe_ids) if msg.recipe_ids else None
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

    def load_history(self, room_id: int) -> list[ModelMessage]:
        messages = (
            self.db.query(ChatMessage)
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

    def load_recent_history(self, room_id: int, limit: int) -> list[ModelMessage]:
        return self.load_history(room_id)[-limit:]

    def save_messages(
        self,
        room_id: int,
        user_content: str,
        ai_content: str,
        recipe_ids: list[int] | None = None,
    ) -> int:
        self.db.add(ChatMessage(room_id=room_id, role="user", content=user_content))
        ai_message = ChatMessage(
            room_id=room_id,
            role="model",
            content=ai_content,
            recipe_ids=recipe_ids,
        )
        self.db.add(ai_message)
        self.db.commit()
        self.db.refresh(ai_message)
        return ai_message.message_id

    def _get_recipes(self, recipe_ids: list[int]) -> list[RecipeResponse]:
        recipe_rows = (
            self.db.query(Recipe)
            .filter(Recipe.recipe_id.in_(recipe_ids), Recipe.is_active.is_(True))
            .all()
        )
        return [RecipeResponse.model_validate(recipe) for recipe in recipe_rows]
