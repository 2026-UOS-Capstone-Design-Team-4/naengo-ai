import json
from typing import Any


class StreamEventBuilder:
    def event(self, event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def metadata(
        self,
        intent_type: str,
        model: str,
        extra: dict[str, Any] | None = None,
    ) -> str:
        payload = {"intent_type": intent_type, "model": model}
        if extra:
            payload.update(extra)
        return self.event("metadata", payload)

    def message(self, content: str) -> str:
        return self.event("message", {"content": content})

    def profile_update(self, payload: dict[str, Any]) -> str:
        return self.event("profile_update", payload)

    def recipes(self, recipes: list[dict]) -> str:
        return self.event("recipes", recipes)

    def done(self, message_id: int, recipe_ids: list[int]) -> str:
        return self.event(
            "done",
            {"message_id": message_id, "recipe_ids": recipe_ids},
        )

    def error(self, code: str, message: str) -> str:
        return self.event("error", {"code": code, "message": message})


stream_event_builder = StreamEventBuilder()
