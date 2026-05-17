import re

from app.agents.core.system_prompts import (
    ACK_SMALLTALK_MESSAGE,
    BYE_SMALLTALK_MESSAGE,
    DEFAULT_SMALLTALK_MESSAGE,
    GREETING_SMALLTALK_MESSAGE,
    LAUGH_SMALLTALK_MESSAGE,
    THANKS_SMALLTALK_MESSAGE,
)

_THANKS_PATTERN = re.compile(r"(고마워|감사|thanks|thank\s*you)", re.IGNORECASE)
_ACK_PATTERN = re.compile(r"^(좋아|굿|오케|ㅇㅋ|ok|okay)[\s!~.]*$", re.IGNORECASE)
_LAUGH_PATTERN = re.compile(r"^(ㅎㅎ|ㅋㅋ|ㅎ+|ㅋ+)[\s!~.]*$", re.IGNORECASE)
_BYE_PATTERN = re.compile(r"(bye|잘\s*있어|다음에\s*봐)", re.IGNORECASE)
_GREETING_PATTERN = re.compile(r"(안녕|ㅎㅇ|hi\b|hello|반가워)", re.IGNORECASE)


class SmalltalkResponder:
    def respond(self, message: str) -> str:
        stripped = message.strip()
        if _THANKS_PATTERN.search(stripped):
            return THANKS_SMALLTALK_MESSAGE
        if _ACK_PATTERN.search(stripped):
            return ACK_SMALLTALK_MESSAGE
        if _LAUGH_PATTERN.search(stripped):
            return LAUGH_SMALLTALK_MESSAGE
        if _BYE_PATTERN.search(stripped):
            return BYE_SMALLTALK_MESSAGE
        if _GREETING_PATTERN.search(stripped):
            return GREETING_SMALLTALK_MESSAGE
        return DEFAULT_SMALLTALK_MESSAGE


smalltalk_responder = SmalltalkResponder()
