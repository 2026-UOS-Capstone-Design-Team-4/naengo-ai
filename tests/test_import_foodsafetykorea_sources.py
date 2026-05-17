from scripts.import_foodsafetykorea_sources import (
    _build_source,
)


def test_build_foodsafetykorea_source_uses_dataset_identity():
    row = {
        "id": "28",
        "name": "새우 두부 계란찜",
        "nutrition": {"calories": "220"},
    }

    source = _build_source(row, "28")

    assert source.source_type == "PUBLIC_DATA"
    assert source.parser_type == "DATASET"
    assert source.source_site == "foodsafetykorea"
    assert source.source_record_id == "28"
    assert source.source_dataset_id == "foodsafetykorea-recipe"


def test_build_foodsafetykorea_source_keeps_extraction_for_separate_script():
    row = {
        "id": "28",
        "name": "새우 두부 계란찜",
        "method": "찌기",
        "category": "반찬",
        "serving_weight": "120",
        "nutrition": {
            "calories": "220",
            "carbohydrate": "3",
            "protein": "14",
            "fat": "17",
            "sodium": "99",
        },
        "ingredients": "두부 75g, 새우 30g\n고명\n시금치 10g",
        "manual_steps": [
            {
                "step": 1,
                "description": "1. 새우를 데칩니다.",
                "image_url": "https://example.com/step.jpg",
            }
        ],
        "low_sodium_tip": "소금 대신 향이 있는 재료로 맛을 냅니다.",
        "image_small_url": "https://example.com/small.jpg",
        "image_large_url": "https://example.com/large.jpg",
    }

    source = _build_source(row, "28")

    assert source.parse_status == "NOT_PARSED"
    assert source.extraction is None
    assert source.raw_payload == row
