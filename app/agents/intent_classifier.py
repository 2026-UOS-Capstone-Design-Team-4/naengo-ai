import re
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core import config

INTENT_TYPE = Literal[
    "RECIPE_RECOMMENDATION",
    "RECIPE_DETAIL_QUESTION",
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "DIET_OR_ALLERGY",
    "PROFILE_UPDATE",
    "IMAGE_BASED_RECIPE",
    "IDENTITY_OR_HELP",
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
    r"(넌\s*누구|너\s*누구|네\s*이름|너의\s*이름|당신\s*누구|이름이\s*뭐|어떤\s*ai|무슨\s*ai|어느\s*회사|어떤\s*모델"
    r"|너는\s*뭐|넌\s*뭐|당신은\s*뭐|뭐\s*하는\s*(?:ai|프로그램|봇|것|거)"
    r"|who\s*are\s*you|what\s*are\s*you|your\s*name|what'?s\s*your\s*name"
    r"|gpt|chatgpt|claude|gemini|openai|google|anthropic)",
    re.IGNORECASE,
)

_SMALLTALK_PATTERN = re.compile(
    r"^(안녕|ㅎㅎ|ㅋㅋ|ㅎ+|고마워|감사|수고|굿|좋아|오케|ㅇㅋ|반가워|잘\s*있어|잘\s*지내|bye|hi\b|hello|thanks|thank\s*you)[\s!~]*$",
    re.IGNORECASE,
)

_INTENT_CLASSIFIER_SYSTEM_PROMPT = """
너는 사용자의 채팅 메시지가 어떤 의도인지 분류하는 전문가야.

## Intent Types

- RECIPE_RECOMMENDATION: 재료/상황/기분 기반 레시피 추천 요청
- RECIPE_DETAIL_QUESTION: 특정 레시피에 대한 질문
- COOKING_TIP: 조리 팁, 요리 방법 질문
- INGREDIENT_SUBSTITUTION: 대체 재료 질문
- DIET_OR_ALLERGY: 식단, 알레르기, 식이 제한 관련
- PROFILE_UPDATE: 취향, 알레르기, 선호 정보 갱신 요청
- IMAGE_BASED_RECIPE: 이미지 기반 레시피 추천 요청
- IDENTITY_OR_HELP: 서비스 정체성/사용법 질문
- SMALLTALK: 가벼운 인사, 감사 등 요리와 무관한 가벼운 대화
- OFF_TOPIC: 요리, 식재료, 식단과 완전히 무관한 주제

## 규칙
- confidence는 0.0~1.0 사이 float
- reason은 한 문장으로 간결하게
- 요리 관련이면 is_cooking_related=true
""".strip()


class IntentClassifier:
    def __init__(self) -> None:
        model = OpenAIModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=IntentResult,
            system_prompt=_INTENT_CLASSIFIER_SYSTEM_PROMPT,
        )

    async def classify(
        self, message: str, history: list[ModelMessage]
    ) -> IntentResult:
        if _IDENTITY_PATTERN.search(message):
            return IntentResult(
                is_cooking_related=False,
                intent_type="IDENTITY_OR_HELP",
                confidence=1.0,
                reason="아이덴티티/도움말 패턴 감지",
            )

        if _SMALLTALK_PATTERN.match(message.strip()):
            return IntentResult(
                is_cooking_related=False,
                intent_type="SMALLTALK",
                confidence=0.95,
                reason="스몰톡 패턴 감지",
            )

        result = await self._agent.run(message, message_history=history)
        return result.output  # type: ignore[return-value]


intent_classifier = IntentClassifier()
