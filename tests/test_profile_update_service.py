from types import SimpleNamespace

from app.services.profile_update_service import (
    ProfileUpdateAction,
    ProfileUpdateAIOutput,
    ProfileUpdateAIOutputCandidate,
    ProfileUpdateAnalyzer,
    ProfileUpdateOperation,
)


class FakeAgent:
    def __init__(self, output: ProfileUpdateAIOutput):
        self.output = output
        self.prompt = None

    def run_sync(self, prompt: str):
        self.prompt = prompt
        return SimpleNamespace(output=self.output)


def test_ai_profile_update_auto_saves_structured_candidate():
    agent = FakeAgent(
        ProfileUpdateAIOutput(
            action=ProfileUpdateAction.AUTO_SAVE,
            candidates=[
                ProfileUpdateAIOutputCandidate(
                    field="allergies",
                    operation=ProfileUpdateOperation.ADD,
                    value="새우",
                    evidence="나 새우 알러지 있어",
                    confidence=0.97,
                    scope="long_term",
                    subject="self",
                )
            ],
        )
    )

    decision = ProfileUpdateAnalyzer(agent).analyze("나 새우 알러지 있어")

    assert decision.action == ProfileUpdateAction.AUTO_SAVE
    assert decision.candidates[0].field == "allergies"
    assert decision.candidates[0].value == "새우"
    assert "[User message]\n나 새우 알러지 있어" in agent.prompt


def test_ai_profile_update_ignores_negation():
    agent = FakeAgent(ProfileUpdateAIOutput(action=ProfileUpdateAction.IGNORE))

    decision = ProfileUpdateAnalyzer(agent).analyze("나는 계란 알레르기는 없어")

    assert decision.action == ProfileUpdateAction.IGNORE
    assert decision.candidates == []


def test_ai_profile_update_requires_confirmation_for_health_context():
    agent = FakeAgent(
        ProfileUpdateAIOutput(
            action=ProfileUpdateAction.REQUIRE_CONFIRMATION,
            candidates=[
                ProfileUpdateAIOutputCandidate(
                    field="dietary_restrictions",
                    operation=ProfileUpdateOperation.ADD,
                    value="저탄수화물",
                    evidence="당뇨 때문에 탄수화물을 줄여야 해",
                    confidence=0.78,
                    scope="long_term",
                    subject="self",
                    reason="건강 상태와 연결된 식단 정보라 확인이 필요함",
                )
            ],
        )
    )

    decision = ProfileUpdateAnalyzer(agent).analyze(
        "당뇨 때문에 탄수화물을 줄여야 해"
    )

    assert decision.action == ProfileUpdateAction.REQUIRE_CONFIRMATION
    assert decision.candidates[0].field == "dietary_restrictions"
    assert "건강 상태" in decision.candidates[0].reason


def test_ai_profile_update_receives_current_profile_context():
    profile = SimpleNamespace(
        allergies=[],
        dietary_restrictions=[],
        preferred_ingredients=[],
        disliked_ingredients=["고수"],
        preferred_categories=[],
        taste_keywords=[],
        cooking_skill=None,
        preferred_cooking_time_minutes=None,
        serving_size=None,
    )
    agent = FakeAgent(ProfileUpdateAIOutput(action=ProfileUpdateAction.IGNORE))

    ProfileUpdateAnalyzer(agent).analyze("나는 고수 좋아해", profile=profile)

    assert "'disliked_ingredients': ['고수']" in agent.prompt
