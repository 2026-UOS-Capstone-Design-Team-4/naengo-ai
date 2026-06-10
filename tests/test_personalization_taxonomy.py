from app.services.personalization_taxonomy import (
    canonicalize_profile_value,
    extract_canonical_diet_keywords,
)


def test_taxonomy_canonicalizes_profile_values():
    assert canonicalize_profile_value("dietary_restrictions", "저탄수화물") == (
        "low_carb"
    )
    assert canonicalize_profile_value("taste_keywords", "칼칼") == "spicy"
    assert canonicalize_profile_value("allergies", "계란") == "달걀"
    assert canonicalize_profile_value("preferred_ingredients", "두부") == "두부"


def test_extract_diet_keywords_uses_only_current_request_text():
    assert extract_canonical_diet_keywords(
        "오늘은 저탄수 비건 레시피를 추천해줘"
    ) == ["vegan", "low_carb"]
    assert extract_canonical_diet_keywords("비건 말고 일반식 추천해줘") == []
