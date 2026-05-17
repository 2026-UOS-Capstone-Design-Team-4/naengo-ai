from types import SimpleNamespace

from app.agents.core.user_context import UserContextBuilder


def test_build_from_profile_returns_structured_context():
    profile = SimpleNamespace(
        allergies=["새우"],
        disliked_ingredients=["고수"],
        preferred_ingredients=["두부"],
        dietary_restrictions=["저탄수화물"],
        taste_keywords=["매운"],
        cooking_skill="easy",
        preferred_cooking_time_minutes=15,
    )

    context = UserContextBuilder().build_from_profile(profile)

    assert context == "\n".join(
        [
            "알레르기: 새우",
            "싫어하는 재료: 고수",
            "좋아하는 재료: 두부",
            "식이 제한: 저탄수화물",
            "선호 맛: 매운",
            "요리 수준: 초급",
            "선호 조리 시간: 15분 이내",
        ]
    )


def test_build_from_profile_returns_none_when_empty():
    profile = SimpleNamespace(
        allergies=None,
        disliked_ingredients=None,
        preferred_ingredients=None,
        dietary_restrictions=None,
        taste_keywords=None,
        cooking_skill=None,
        preferred_cooking_time_minutes=None,
    )

    assert UserContextBuilder().build_from_profile(profile) is None
