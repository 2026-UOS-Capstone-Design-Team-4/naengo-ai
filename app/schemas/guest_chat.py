from typing import Literal

from pydantic import BaseModel, Field, field_validator

from pydantic_ai.messages import (
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

_IMAGE_EXAMPLE = "data:image/jpeg;base64,/9j/4AAQSkZJRgAB..."
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _validate_image(v: str | None) -> str | None:
    if v is None:
        return v
    if len(v.encode()) > _MAX_IMAGE_BYTES * 4 // 3:
        raise ValueError("이미지 크기는 10MB를 초과할 수 없습니다.")
    return v


class GuestHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    image: str | None = None

    @field_validator("image")
    @classmethod
    def validate_image_size(cls, v: str | None) -> str | None:
        return _validate_image(v)


class GuestChatRequest(BaseModel):
    prompt: str
    image: str | None = None
    history: list[GuestHistoryMessage] = Field(default_factory=list, max_length=20)

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "이 재료들로 뭘 만들 수 있어?",
                "image": _IMAGE_EXAMPLE,
                "history": [
                    {
                        "role": "user",
                        "content": "냉장고 사진이에요",
                        "image": _IMAGE_EXAMPLE,
                    },
                    {
                        "role": "assistant",
                        "content": "김치와 두부가 보이네요! 김치찌개 어떠세요?",
                        "image": None,
                    },
                ],
            }
        }
    }

    @field_validator("image")
    @classmethod
    def validate_image_size(cls, v: str | None) -> str | None:
        return _validate_image(v)


def history_to_model_messages(history: list[GuestHistoryMessage]) -> list[ModelMessage]:
    result: list[ModelMessage] = []
    for msg in history:
        if msg.role == "user":
            content = (
                [msg.content, ImageUrl(url=msg.image)] if msg.image else msg.content
            )
            result.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            result.append(ModelResponse(parts=[TextPart(content=msg.content)]))
    return result
