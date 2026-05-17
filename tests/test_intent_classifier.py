import asyncio

from app.agents.intent.intent_classifier import IntentClassifier


def test_identity_prompt_is_classified_without_model_call():
    result = asyncio.run(IntentClassifier().classify("너는 누구야?", history=[]))

    assert result.intent_type == "IDENTITY"
    assert result.is_cooking_related is False
    assert result.confidence == 1.0


def test_smalltalk_prompt_is_classified_without_model_call():
    result = asyncio.run(IntentClassifier().classify("ㅎㅇ", history=[]))

    assert result.intent_type == "SMALLTALK"
    assert result.is_cooking_related is False
    assert result.confidence >= 0.95
