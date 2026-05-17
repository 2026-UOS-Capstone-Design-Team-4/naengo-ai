from types import SimpleNamespace

from app.services.profile_update_service import (
    ProfileUpdateAction,
    ProfileUpdateExtractor,
    ProfileUpdatePolicy,
)


def decide(message: str, profile=None):
    extractor = ProfileUpdateExtractor()
    policy = ProfileUpdatePolicy()
    return policy.decide(extractor.extract(message), profile)


def test_self_allergy_is_auto_save():
    decision = decide("나 새우 알레르기 있어")

    assert decision.action == ProfileUpdateAction.AUTO_SAVE
    assert decision.candidates[0].field == "allergies"
    assert decision.candidates[0].value == "새우"


def test_self_disliked_ingredient_is_auto_save():
    decision = decide("나는 고수 싫어해")

    assert decision.action == ProfileUpdateAction.AUTO_SAVE
    assert decision.candidates[0].field == "disliked_ingredients"
    assert decision.candidates[0].value == "고수"


def test_preferred_cooking_time_is_auto_save():
    decision = decide("앞으로 15분 안에 되는 요리 위주로 추천해줘")

    assert decision.action == ProfileUpdateAction.AUTO_SAVE
    assert decision.candidates[0].field == "preferred_cooking_time_minutes"
    assert decision.candidates[0].value == 15


def test_other_person_info_is_ignored():
    decision = decide("새우 알레르기 있는 친구가 와")

    assert decision.action == ProfileUpdateAction.IGNORE


def test_temporary_preference_requires_no_auto_save():
    decision = decide("오늘은 고수 싫어")

    assert decision.action == ProfileUpdateAction.REQUIRE_CONFIRMATION
    assert "일시적인 조건" in decision.candidates[0].reason


def test_health_related_diet_requires_confirmation():
    decision = decide("당뇨 때문에 탄수화물을 줄여야 해")

    assert decision.action == ProfileUpdateAction.REQUIRE_CONFIRMATION
    assert decision.candidates[0].field == "dietary_restrictions"
    assert "건강 상태" in decision.candidates[0].reason


def test_profile_conflict_requires_confirmation():
    profile = SimpleNamespace(
        preferred_ingredients=[],
        disliked_ingredients=["고수"],
    )

    decision = decide("나는 고수 좋아해", profile=profile)

    assert decision.action == ProfileUpdateAction.REQUIRE_CONFIRMATION
    assert "기존 프로필" in decision.candidates[0].reason
