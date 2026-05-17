import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from app.agents.intent.intent_classifier import IntentResult
from app.agents.recipe.search_planner import SearchPlan
from app.services.agent_service import AgentService
from app.services.live_research_service import LiveResearchResult, ResearchEvidence


class FakeIntentClassifier:
    def __init__(self, result: IntentResult):
        self.result = result
        self.calls: list[str] = []

    async def classify(self, message, history):
        self.calls.append(message)
        return self.result


@dataclass
class FakeQuery:
    prompt: str
    intent_type: str


class FakeLiveResearchService:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.should_research_calls: list[tuple[str, str]] = []
        self.build_query_calls: list[tuple[str, str]] = []
        self.research_calls: list[FakeQuery] = []

    def should_research(self, intent_type: str, message: str) -> bool:
        self.should_research_calls.append((intent_type, message))
        return self.enabled

    def build_query(self, message: str, intent_type: str) -> FakeQuery:
        self.build_query_calls.append((message, intent_type))
        return FakeQuery(prompt=message, intent_type=intent_type)

    def research(self, query: FakeQuery) -> LiveResearchResult:
        self.research_calls.append(query)
        evidence = [
            ResearchEvidence(
                title="요즘 인기 레시피",
                url="https://example.com/trend",
                publisher="Example",
                published_at="2026-05-16",
                fetched_at=datetime.now(UTC),
                summary="SNS에서 자주 언급되는 조합입니다.",
                confidence=0.9,
            )
        ]
        return LiveResearchResult(
            answer_context="Live research evidence",
            evidence=evidence,
            used_at=datetime.now(UTC),
            cache_key="test",
        )


class FakeChatService:
    def __init__(self):
        self.saved = []

    def save_messages(
        self,
        room_id,
        user_content,
        model_content,
        recipe_ids=None,
        image_url=None,
    ):
        self.saved.append(
            (room_id, user_content, model_content, recipe_ids, image_url)
        )
        return 123


class FakeSearchPlanner:
    async def plan(self, message, history, user_profile_context=None):
        return SearchPlan(
            query_text="김치 두부 찌개",
            available_ingredients=["김치", "두부"],
            main_ingredients=["김치", "두부"],
        )


class FakeUserContextBuilder:
    def build_profile_context(self, db, user_id):
        return None


class FakeRecipe:
    title = "김치두부찌개"


class FakeRecipeRetrievalService:
    def __init__(self):
        self.queries = []

    def search_recipes(self, query, limit=3, plan=None):
        self.queries.append((query, limit, plan))
        return [FakeRecipe()]

    def recipe_to_payload(self, recipe):
        return {
            "id": 7,
            "title": recipe.title,
            "description": "칼칼한 찌개",
            "ingredients_raw": "김치, 두부",
            "cooking_time_minutes": 20,
            "difficulty": "easy",
            "category": ["한식"],
        }


def _parse_events(chunks: list[str]) -> list[tuple[str, dict]]:
    events = []
    for chunk in chunks:
        event_name = None
        data = None
        for line in chunk.strip().splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        if event_name is not None and data is not None:
            events.append((event_name, data))
    return events


async def _collect_stream(service: AgentService, prompt: str, chat_service):
    return [
        chunk
        async for chunk in await service.stream(
            prompt=prompt,
            image=None,
            room_id=1,
            history=[],
            user_id=1,
            chat_service=chat_service,
            db=None,
        )
    ]


def test_fresh_recipe_query_uses_live_research_before_clarification(monkeypatch):
    classifier = FakeIntentClassifier(
        IntentResult(
            is_cooking_related=True,
            intent_type="RECIPE_RECOMMENDATION",
            confidence=0.4,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=True)
    monkeypatch.setattr("app.services.agent_service.intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chat_service = FakeChatService()
    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "요즘 유행하는 다이어트 요리 추천해줘",
            chat_service,
        )
    )

    events = _parse_events(chunks)
    assert events[0][0] == "metadata"
    assert events[0][1]["intent_type"] == "RECIPE_RECOMMENDATION"
    assert events[0][1]["used_live_research"] is True
    assert events[0][1]["source_count"] == 1
    assert events[1][0] == "message"
    assert "구체적으로" in events[1][1]["content"]
    assert events[2] == ("done", {"message_id": 123, "recipe_ids": []})
    assert live_research.build_query_calls == [
        ("요즘 유행하는 다이어트 요리 추천해줘", "RECIPE_RECOMMENDATION")
    ]
    assert len(live_research.research_calls) == 1


def test_regular_recipe_query_does_not_use_live_research(monkeypatch):
    classifier = FakeIntentClassifier(
        IntentResult(
            is_cooking_related=True,
            intent_type="RECIPE_RECOMMENDATION",
            confidence=0.4,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    monkeypatch.setattr("app.services.agent_service.intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chunks = asyncio.run(
        _collect_stream(AgentService(), "김치랑 두부 있어", FakeChatService())
    )

    events = _parse_events(chunks)
    assert events[0][0] == "metadata"
    assert events[0][1]["used_live_research"] is False
    assert events[0][1]["source_count"] == 0
    assert live_research.build_query_calls == []
    assert live_research.research_calls == []


def test_off_topic_query_keeps_live_research_off(monkeypatch):
    classifier = FakeIntentClassifier(
        IntentResult(
            is_cooking_related=False,
            intent_type="OFF_TOPIC",
            confidence=1.0,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    monkeypatch.setattr("app.services.agent_service.intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chunks = asyncio.run(
        _collect_stream(AgentService(), "요즘 주식 뭐 사야 돼?", FakeChatService())
    )

    events = _parse_events(chunks)
    assert events[0][1]["intent_type"] == "OFF_TOPIC"
    assert events[0][1]["used_live_research"] is False
    assert events[1][0] == "message"
    assert "요리" in events[1][1]["content"]


def test_recipe_query_prefetches_rag_even_when_agent_does_not_call_tool(monkeypatch):
    classifier = FakeIntentClassifier(
        IntentResult(
            is_cooking_related=True,
            intent_type="RECIPE_RECOMMENDATION",
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    retrieval = FakeRecipeRetrievalService()
    captured = {}

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        captured["user_prompt"] = user_prompt
        captured["deps"] = deps
        await queue.put(("text", "추천 레시피를 찾았어요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_search_planner",
        FakeSearchPlanner(),
    )
    monkeypatch.setattr(
        "app.services.agent_service.user_context_builder",
        FakeUserContextBuilder(),
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_retrieval_service",
        retrieval,
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(
        _collect_stream(AgentService(), "김치랑 두부 있어", FakeChatService())
    )

    events = _parse_events(chunks)
    assert retrieval.queries[0][:2] == ("김치 두부 찌개", 3)
    assert retrieval.queries[0][2].available_ingredients == ["김치", "두부"]
    assert retrieval.queries[0][2].main_ingredients == ["김치", "두부"]
    assert "RAG recipe candidates" in captured["user_prompt"]
    assert captured["deps"].last_found_recipes[0]["id"] == 7
    assert ("recipes", [captured["deps"].last_found_recipes[0]]) in events
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": [7]})
