from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.recipe import RecipeResponse


class ChatRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    role: str
    content: str
    recipes: list[RecipeResponse] | None = None
    created_at: datetime


class ChatRequest(BaseModel):
    prompt: str
    image: str | None = None  # base64 data URL (e.g. "data:image/jpeg;base64,...")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "냉장고 사진이에요. 어떤 요리를 만들 수 있을까요?",
                "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgAB...",
            }
        }
    }
