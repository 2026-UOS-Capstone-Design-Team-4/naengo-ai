from types import SimpleNamespace

from scripts import parse_10000recipe_sources


class FakeDb:
    def __init__(self):
        self.deleted = []

    def commit(self):
        pass

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        pass


def test_process_source_does_not_keep_extraction_when_kcal_per_serving_is_missing(
    monkeypatch,
):
    source = SimpleNamespace(
        source_id=1,
        raw_payload={
            "title": "test recipe",
            "ingredients": [{"name": "salt", "amount": "1T"}],
            "instructions": [{"step_no": 1, "instruction": "Cook it."}],
            "servings_raw": "1 serving",
            "cooking_time_raw": "10 min",
        },
        raw_content_hash=None,
        extraction=None,
        parse_status="NOT_PARSED",
        review_status="PENDING",
        validation_errors=[],
        parsed_at=None,
        extraction_version=None,
    )

    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_recipe_metadata",
        lambda *args: parse_10000recipe_sources.EstimatedRecipeMetadata(),
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_difficulty",
        lambda *args: "easy",
    )

    result = parse_10000recipe_sources.process_source(FakeDb(), source)

    assert result == "INVALID"
    assert source.extraction is None
    assert source.validation_errors == [
        {"code": "PARSE_ERROR", "message": "kcal_per_serving could not be estimated."}
    ]
