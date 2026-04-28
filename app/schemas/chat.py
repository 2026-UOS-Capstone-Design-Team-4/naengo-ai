from typing import Literal

from pydantic import BaseModel, Field


class ChatPart(BaseModel):
    text: str


class ChatContent(BaseModel):
    role: Literal["user", "model"]
    parts: list[ChatPart]


class ChatRequest(BaseModel):
    prompt: str
    history: list[ChatContent] | None = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "냉장고에 계란이랑 김치가 있어요",
                "history": [
                    {"role": "user", "parts": [{"text": "안녕하세요!"}]},
                    {
                        "role": "model",
                        "parts": [{"text": "안녕하세요! 어떤 재료가 있으신가요?"}],
                    },
                ],
            }
        }
    }
