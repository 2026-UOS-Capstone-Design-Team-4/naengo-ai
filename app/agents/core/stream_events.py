import json
from typing import Any

from fastapi.encoders import jsonable_encoder


class StreamEventBuilder:
    def event(self, event: str, data: Any) -> str:
        encoded = jsonable_encoder(data)
        return f"event: {event}\ndata: {json.dumps(encoded, ensure_ascii=False)}\n\n"

    def metadata(
        self,
        primary_task: str,
        model: str,
        extra: dict[str, Any] | None = None,
    ) -> str:
        payload = {"primary_task": primary_task, "model": model}
        if extra:
            payload.update(extra)
        return self.event("metadata", payload)

    def message(self, content: str) -> str:
        return self.event("message", {"content": content})

    def profile_update(self, payload: dict[str, Any]) -> str:
        return self.event("profile_update", payload)

    def planning(self, payload: dict[str, Any]) -> str:
        return self.event("planning", payload)

    def workflow(self, payload: dict[str, Any]) -> str:
        return self.event("workflow", payload)

    def retrieval(self, payload: dict[str, Any]) -> str:
        return self.event("retrieval", payload)

    def evidence(self, payload: dict[str, Any]) -> str:
        return self.event("evidence", payload)

    def context(self, payload: dict[str, Any]) -> str:
        return self.event("context", payload)

    def recipes(self, recipes: list[dict]) -> str:
        return self.event("recipes", recipes)

    def done(self, message_id: int | None, recipe_ids: list[int]) -> str:
        return self.event(
            "done",
            {"message_id": message_id, "recipe_ids": recipe_ids},
        )

    def error(self, code: str, message: str) -> str:
        return self.event("error", {"code": code, "message": message})


stream_event_builder = StreamEventBuilder()
