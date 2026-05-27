import json
from decimal import Decimal

from app.agents.core.stream_events import StreamEventBuilder


def parse_sse(payload: str):
    lines = payload.strip().splitlines()
    event = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event, data


def test_message_event_uses_sse_format_and_utf8_json():
    event, data = parse_sse(StreamEventBuilder().message("안녕하세요"))

    assert event == "message"
    assert data == {"content": "안녕하세요"}


def test_done_event_includes_message_id_and_recipe_ids():
    event, data = parse_sse(StreamEventBuilder().done(10, [1, 2]))

    assert event == "done"
    assert data == {"message_id": 10, "recipe_ids": [1, 2]}


def test_metadata_event_merges_extra_payload():
    event, data = parse_sse(
        StreamEventBuilder().metadata(
            "RECIPE_FIND",
            "test-model",
            extra={"source_count": 2},
        )
    )

    assert event == "metadata"
    assert data == {
        "primary_task": "RECIPE_FIND",
        "model": "test-model",
        "source_count": 2,
    }


def test_recipes_event_serializes_decimal_values():
    event, data = parse_sse(
        StreamEventBuilder().recipes(
            [
                {
                    "id": 1,
                    "title": "삼겹살 구이",
                    "ingredients": [{"name": "삼겹살", "quantity": Decimal("1.5")}],
                }
            ]
        )
    )

    assert event == "recipes"
    assert data[0]["ingredients"][0]["quantity"] == 1.5


def test_planning_event_includes_answer_strategy():
    event, data = parse_sse(
        StreamEventBuilder().planning(
            {
                "primary_task": "RECIPE_FIND",
                "sub_intent": "BY_INGREDIENTS",
                "answer_strategy": "RECIPE_RECOMMENDATION",
                "planner": "RecipeFindPlanner",
                "selected_agent": "recipe_agent",
            }
        )
    )

    assert event == "planning"
    assert data["primary_task"] == "RECIPE_FIND"
    assert data["sub_intent"] == "BY_INGREDIENTS"
    assert data["answer_strategy"] == "RECIPE_RECOMMENDATION"
    assert data["selected_agent"] == "recipe_agent"


def test_retrieval_event_reports_counts():
    event, data = parse_sse(
        StreamEventBuilder().retrieval(
            {"status": "completed", "candidate_count": 30, "selected_count": 3}
        )
    )

    assert event == "retrieval"
    assert data["status"] == "completed"
    assert data["selected_count"] == 3


def test_evidence_event_serializes_recommendation_evidence():
    event, data = parse_sse(
        StreamEventBuilder().evidence(
            {
                "recipes": [
                    {
                        "recipe_id": 1,
                        "title": "김치두부찌개",
                        "why_matched": ["김치", "두부"],
                        "risk_flags": [],
                        "missing_ingredients": [],
                        "time_minutes": 20,
                        "difficulty": "easy",
                    }
                ],
                "constraints": {"avoid_ingredients": ["새우"]},
            }
        )
    )

    assert event == "evidence"
    assert data["recipes"][0]["why_matched"] == ["김치", "두부"]
    assert data["constraints"] == {"avoid_ingredients": ["새우"]}
