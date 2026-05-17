from types import SimpleNamespace

import pytest

from app.services.user_profile_input_service import (
    UserProfileInputNormalizeError,
    UserProfileInputNormalizer,
    UserProfileInputOutput,
)


class FakeAgent:
    def __init__(self, output=None, error: Exception | None = None):
        self.output = output
        self.error = error
        self.prompt = None

    def run_sync(self, prompt: str):
        self.prompt = prompt
        if self.error:
            raise self.error
        return SimpleNamespace(output=self.output)


def test_normalizer_accepts_user_info_and_returns_one_sentence():
    agent = FakeAgent(
        UserProfileInputOutput(
            is_user_info=True,
            normalized_sentence="  새우 알레르기가 있어요.  ",
            reason="allergy",
        )
    )
    normalizer = UserProfileInputNormalizer(agent=agent, model="test-model")

    result = normalizer.normalize("나 새우 알러지 있어")

    assert result.is_user_info is True
    assert result.normalized_sentence == "새우 알레르기가 있어요."
    assert agent.prompt == "나 새우 알러지 있어"


def test_normalizer_rejects_non_user_info():
    normalizer = UserProfileInputNormalizer(
        agent=FakeAgent(
            UserProfileInputOutput(
                is_user_info=False,
                normalized_sentence=None,
                reason="temporary request",
            )
        ),
        model="test-model",
    )

    result = normalizer.normalize("오늘은 닭고기 빼줘")

    assert result.is_user_info is False
    assert result.normalized_sentence is None
    assert result.reason == "temporary request"


def test_normalizer_wraps_agent_errors():
    normalizer = UserProfileInputNormalizer(
        agent=FakeAgent(error=RuntimeError("boom")),
        model="test-model",
    )

    with pytest.raises(UserProfileInputNormalizeError):
        normalizer.normalize("매운 음식 좋아해")
