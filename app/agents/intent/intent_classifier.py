import re
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.system_prompts import INTENT_CLASSIFIER_PROMPT
from app.core import config

INTENT_TYPE = Literal[
    "RECIPE_RECOMMENDATION",
    "RECIPE_DETAIL_QUESTION",
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "DIET_OR_ALLERGY",
    "PROFILE_UPDATE",
    "IMAGE_BASED_RECIPE",
    "IDENTITY",
    "SMALLTALK",
    "OFF_TOPIC",
]

_RECIPE_RELATED_INTENTS = {
    "RECIPE_RECOMMENDATION",
    "RECIPE_DETAIL_QUESTION",
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "DIET_OR_ALLERGY",
    "PROFILE_UPDATE",
    "IMAGE_BASED_RECIPE",
}


class IntentResult(BaseModel):
    is_cooking_related: bool
    intent_type: INTENT_TYPE
    confidence: float
    reason: str


_IDENTITY_PATTERN = re.compile(
    r"(넌\s*누구|너\s*누구|너는\s*누구|네\s*이름|너의\s*이름|당신\s*누구"
    r"|이름이\s*뭐|어떤\s*ai|무슨\s*ai|어느\s*회사|어떤\s*모델"
    r"|너는\s*뭐|넌\s*뭐|당신은\s*뭐|뭐\s*하는\s*(?:ai|프로그램|봇|것|거)"
    r"|who\s*are\s*you|what\s*are\s*you|your\s*name|what'?s\s*your\s*name"
    r"|gpt|chatgpt|claude|gemini|openai|google|anthropic)",
    re.IGNORECASE,
)

class IntentClassifier:
    def __init__(self) -> None:
        model = OpenAIChatModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=IntentResult,
            system_prompt=INTENT_CLASSIFIER_PROMPT,
        )

    async def classify(
        self, message: str, history: list[ModelMessage]
    ) -> IntentResult:
        if _IDENTITY_PATTERN.search(message):
            return IntentResult(
                is_cooking_related=False,
                intent_type="IDENTITY",
                confidence=1.0,
                reason="정체성 질문 패턴 감지",
            )

        result = await self._agent.run(message, message_history=history)
        return result.output  # type: ignore[return-value]


intent_classifier = IntentClassifier()
