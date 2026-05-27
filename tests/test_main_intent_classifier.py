import asyncio
from types import SimpleNamespace

from app.agents.intent.intent_models import MainIntentResult, PrimaryTask
from app.agents.intent.main_intent_classifier import MainIntentClassifier


class FakeIntentAgent:
    def __init__(self, output: MainIntentResult) -> None:
        self.output = output
        self.calls = []

    async def run(self, prompt, message_history):
        self.calls.append((prompt, message_history))
        return SimpleNamespace(output=self.output)


def test_identity_prompt_is_classified_by_model():
    classifier = MainIntentClassifier()
    classifier._agent = FakeIntentAgent(
        MainIntentResult(
            primary_task=PrimaryTask.SERVICE_QA,
            confidence=0.91,
            reason="서비스 정체성 질문",
        )
    )

    result = asyncio.run(classifier.classify("너는 누구야?", history=[]))

    assert result.primary_task == PrimaryTask.SERVICE_QA
    assert classifier._agent.calls


def test_smalltalk_prompt_is_classified_by_model():
    classifier = MainIntentClassifier()
    classifier._agent = FakeIntentAgent(
        MainIntentResult(
            primary_task=PrimaryTask.SMALLTALK,
            confidence=0.9,
            reason="가벼운 인사",
        )
    )

    result = asyncio.run(classifier.classify("ㅎㅇ", history=[]))

    assert result.primary_task == PrimaryTask.SMALLTALK
    assert classifier._agent.calls


def test_brand_mention_with_recipe_request_is_not_short_circuited():
    classifier = MainIntentClassifier()
    classifier._agent = FakeIntentAgent(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
            confidence=0.88,
            reason="브랜드명보다 레시피 추천 요청이 핵심",
        )
    )

    result = asyncio.run(
        classifier.classify(
            "ChatGPT처럼 말고 우리 DB 기준으로 삼겹살 추천해줘",
            history=[],
        )
    )

    assert result.primary_task == PrimaryTask.RECIPE_FIND
    assert classifier._agent.calls
