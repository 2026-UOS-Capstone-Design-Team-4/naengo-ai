import json

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
            "RECIPE_RECOMMENDATION",
            "test-model",
            extra={"source_count": 2},
        )
    )

    assert event == "metadata"
    assert data == {
        "intent_type": "RECIPE_RECOMMENDATION",
        "model": "test-model",
        "source_count": 2,
    }
