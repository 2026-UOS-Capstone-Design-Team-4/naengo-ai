from types import SimpleNamespace

import pytest

from app.models.recipe_source import RecipeSourceExtraction
from scripts import parse_10000recipe_sources


class FakeDb:
    def __init__(self):
        self.commits = 0
        self.deleted = []
        self.flushes = 0

    def commit(self):
        self.commits += 1

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        self.flushes += 1


class FailingTextRewriter:
    def rewrite(self, extraction):
        raise RuntimeError("rewrite failed")


class FakeQuery:
    def __init__(self):
        self.filters = []
        self.order_by_called = False

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self

    def order_by(self, *criteria):
        self.order_by_called = True
        return self


class FakeQueryDb:
    def __init__(self):
        self.query_obj = FakeQuery()

    def query(self, model):
        return self.query_obj


def _source(extraction=None):
    return SimpleNamespace(
        source_id=1,
        raw_payload={"title": "test recipe"},
        raw_content_hash=None,
        extraction=extraction,
        parse_status="NOT_PARSED",
        review_status="PENDING",
        validation_errors=[],
        parsed_at=None,
        extraction_version=None,
    )


def _extraction() -> RecipeSourceExtraction:
    return RecipeSourceExtraction(
        title="test recipe",
        description="test description",
        content_hash="abc123",
    )


def test_process_source_does_not_keep_extraction_when_build_fails(monkeypatch):
    existing = object()
    source = _source(extraction=existing)
    db = FakeDb()

    def fail_build(raw):
        raise RuntimeError("parse failed")

    monkeypatch.setattr(parse_10000recipe_sources, "build_extraction", fail_build)

    result = parse_10000recipe_sources.process_source(db, source)

    assert result == "INVALID"
    assert source.extraction is None
    assert db.deleted == [existing]
    assert source.validation_errors == [
        {"code": "PARSE_ERROR", "message": "parse failed"}
    ]


def test_process_source_does_not_attach_extraction_when_rewrite_fails(monkeypatch):
    source = _source()
    db = FakeDb()

    monkeypatch.setattr(
        parse_10000recipe_sources,
        "build_extraction",
        lambda raw: _extraction(),
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "is_duplicate",
        lambda db, source, extraction: False,
    )
    monkeypatch.setattr(parse_10000recipe_sources, "validate", lambda extraction: [])

    result = parse_10000recipe_sources.process_source(
        db,
        source,
        text_rewriter=FailingTextRewriter(),
    )

    assert result == "INVALID"
    assert source.extraction is None
    assert source.validation_errors == [
        {"code": "REWRITE_ERROR", "message": "rewrite failed"}
    ]


def test_process_source_attaches_extraction_after_successful_processing(monkeypatch):
    source = _source()
    db = FakeDb()
    extraction = _extraction()

    monkeypatch.setattr(
        parse_10000recipe_sources,
        "build_extraction",
        lambda raw: extraction,
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "is_duplicate",
        lambda db, source, extraction: False,
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "validate",
        lambda extraction: ["reviewable"],
    )

    result = parse_10000recipe_sources.process_source(db, source)

    assert result == "REVIEW_REQUIRED"
    assert source.extraction is extraction
    assert source.validation_errors == ["reviewable"]


def test_source_query_without_refresh_only_selects_not_parsed():
    db = FakeQueryDb()

    query = parse_10000recipe_sources.source_query(db, refresh=False)

    assert query.order_by_called
    assert len(query.filters) == 3


def test_source_query_with_refresh_includes_existing_parse_statuses():
    db = FakeQueryDb()

    query = parse_10000recipe_sources.source_query(db, refresh=True)

    assert query.order_by_called
    assert len(query.filters) == 2


def test_openai_client_uses_import_ai_timeout(monkeypatch):
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(parse_10000recipe_sources, "_openai_client", None)
    monkeypatch.setattr(parse_10000recipe_sources, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "RECIPE_IMPORT_AI_TIMEOUT_SECONDS",
        12.5,
    )

    client = parse_10000recipe_sources._get_openai_client()

    assert isinstance(client, FakeOpenAI)
    assert calls[0]["timeout"] == 12.5


def test_normalize_amount_text_converts_attached_korean_tablespoon_units():
    assert parse_10000recipe_sources._normalize_amount_text("1큰술") == "1T"
    assert parse_10000recipe_sources._normalize_amount_text("1큰 술") == "1T"
    assert parse_10000recipe_sources._normalize_amount_text("2 큰술") == "2T"


def test_build_extraction_fails_before_ai_when_required_structure_is_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_recipe_metadata",
        lambda *args: pytest.fail("metadata AI should not be called"),
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_difficulty",
        lambda *args: pytest.fail("difficulty AI should not be called"),
    )

    with pytest.raises(parse_10000recipe_sources.ExtractionBuildError) as exc:
        parse_10000recipe_sources.build_extraction(
            {
                "title": "empty recipe",
                "ingredients": [],
                "instructions": [],
                "servings_raw": "1인분",
                "cooking_time_raw": "10분",
            }
        )

    assert exc.value.errors == [
        {"code": "MISSING_INGREDIENTS", "message": "ingredients are required."},
        {"code": "MISSING_STEPS", "message": "steps are required."},
    ]


def test_build_extraction_normalizes_parsley_family_root_unit(monkeypatch):
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_recipe_metadata",
        lambda *args: parse_10000recipe_sources.EstimatedRecipeMetadata(
            kcal_per_serving=100,
            cooking_time_minutes=15,
        ),
    )
    monkeypatch.setattr(
        parse_10000recipe_sources,
        "estimate_difficulty",
        lambda *args: "easy",
    )

    extraction = parse_10000recipe_sources.build_extraction(
        {
            "title": "파슬리무침",
            "ingredients": [{"name": "파슬리", "amount": "1/2뿌리"}],
            "instructions": [{"step_no": 1, "instruction": "파슬리를 씻는다."}],
            "servings_raw": "1인분",
            "cooking_time_raw": "10분",
        }
    )

    ingredient = extraction.ingredients[0]
    assert ingredient.amount_text == "1/2대"
    assert ingredient.unit == "대"
    assert extraction.cooking_time_minutes == 15
    assert extraction.quality_score.estimated_fields == [
        "kcal_per_serving",
        "cooking_time_minutes",
    ]
