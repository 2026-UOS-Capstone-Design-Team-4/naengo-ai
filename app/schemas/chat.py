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


class ChatResponse(BaseModel):
    message: str
    recipes: list[dict] | None = None
