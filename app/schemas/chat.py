from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

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
    image_url: str | None = None
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

    @field_validator("image")
    @classmethod
    def validate_image_size(cls, v: str | None) -> str | None:
        if v is None:
            return v
        max_original_bytes = 10 * 1024 * 1024  # 10MB
        if len(v.encode()) > max_original_bytes * 4 // 3:
            raise ValueError("이미지 크기는 10MB를 초과할 수 없습니다.")
        return v
