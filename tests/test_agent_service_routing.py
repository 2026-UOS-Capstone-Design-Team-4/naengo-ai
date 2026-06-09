import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

from app.agents.cooking_qa.planner import CookingQAPlan
from app.agents.intent.intent_models import (
    AnswerStrategy,
    CookingQASubIntent,
    MainIntentResult,
    PrimaryTask,
    RecipeFindSubIntent,
)
from app.agents.recipe.recipe_agent import (
    ingredient_substitution_agent,
    smalltalk_agent,
)
from app.agents.recipe.search_planner import SearchPlan
from app.services.agent_service import AgentService
from app.services.live_research_service import LiveResearchResult, ResearchEvidence
from app.services.profile_update_service import (
    ProfileUpdateAction,
    ProfileUpdateCandidate,
    ProfileUpdateDecision,
    ProfileUpdateOperation,
)


class FakeIntentClassifier:
    def __init__(self, result: MainIntentResult):
        self.result = result
        self.calls: list[str] = []

    async def classify(self, message, history, image=None):
        self.calls.append(message)
        return self.result


@dataclass
class FakeQuery:
    prompt: str
    primary_task: PrimaryTask


class FakeLiveResearchService:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.should_research_calls: list[tuple[PrimaryTask, str]] = []
        self.build_query_calls: list[tuple[str, PrimaryTask]] = []
        self.research_calls: list[FakeQuery] = []

    def should_research(self, primary_task: PrimaryTask, message: str) -> bool:
        self.should_research_calls.append((primary_task, message))
        return self.enabled

    def build_query(self, message: str, primary_task: PrimaryTask) -> FakeQuery:
        self.build_query_calls.append((message, primary_task))
        return FakeQuery(prompt=message, primary_task=primary_task)

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


class FakeProfileUpdateAnalyzer:
    def __init__(self, decision: ProfileUpdateDecision | None = None):
        self.decision = decision

    def analyze(self, message, profile=None):
        return self.decision or ProfileUpdateDecision(ProfileUpdateAction.IGNORE, [])


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
        self.saved.append((room_id, user_content, model_content, recipe_ids, image_url))
        return 123


class FakeScalarResult:
    def scalars(self):
        return []


class FakeDb:
    def __init__(self):
        self.profile = SimpleNamespace(
            user_id=1,
            user_input=[],
            allergies=[],
            dietary_restrictions=[],
            preferred_ingredients=[],
            disliked_ingredients=[],
            preferred_categories=[],
            taste_keywords=[],
            cooking_skill=None,
            preferred_cooking_time_minutes=None,
            serving_size=None,
        )
        self.commits = 0

    def query(self, model):
        return self

    def filter_by(self, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.profile

    def add(self, profile):
        self.profile = profile

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, profile):
        return None

    def execute(self, statement):
        return FakeScalarResult()


class FakeSearchPlanner:
    async def plan(
        self,
        message,
        history,
        user_profile_context=None,
        memory_context=None,
        image=None,
    ):
        return SearchPlan(
            query_text="김치 두부 찌개",
            available_ingredients=["김치", "두부"],
            main_ingredients=["김치", "두부"],
        )


class FakeNoRetrievalSearchPlanner:
    async def plan(
        self,
        message,
        history,
        user_profile_context=None,
        memory_context=None,
        image=None,
    ):
        return SearchPlan(
            query_text="검색 없이 답변",
            retrieval_required=False,
        )


class FakeClarifyingSearchPlanner:
    async def plan(
        self,
        message,
        history,
        user_profile_context=None,
        memory_context=None,
        image=None,
    ):
        return SearchPlan(
            query_text="모호한 추천 요청",
            sub_intent=RecipeFindSubIntent.CLARIFICATION,
            retrieval_required=False,
            clarification_required=True,
            clarification_question="어떤 재료를 기준으로 추천해드릴까요?",
            answer_strategy=AnswerStrategy.CLARIFICATION,
        )


class FakeCookingQAPlanner:
    async def plan(self, message, history, memory_context=None):
        return CookingQAPlan(
            sub_intent=CookingQASubIntent.INGREDIENT_SUBSTITUTION,
            question_type="INGREDIENT_SUBSTITUTION",
            rewritten_question="두부 대신 쓸 재료",
            referenced_ingredients=["두부"],
            needs_retrieval=True,
        )


class FakeClarifyingCookingQAPlanner:
    async def plan(self, message, history, memory_context=None):
        return CookingQAPlan(
            sub_intent=CookingQASubIntent.GENERAL,
            question_type="GENERAL",
            rewritten_question=message,
            clarification_required=True,
            clarification_question="어떤 레시피를 말씀하시는지 알려주세요?",
            answer_strategy=AnswerStrategy.GENERAL_COOKING_QA,
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

    def recipe_to_payload(self, recipe, liked_ids=None, scrapped_ids=None):
        return {
            "id": 7,
            "title": recipe.title,
            "description": "칼칼한 찌개",
            "ingredients": [{"name": "김치"}, {"name": "두부"}],
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


def _legacy_events(events: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    return [event for event in events if event[0] != "workflow"]


async def _collect_stream(service: AgentService, prompt: str, chat_service, db=None):
    return [
        chunk
        async for chunk in await service.stream(
            prompt=prompt,
            image=None,
            room_id=1,
            history=[],
            user_id=1,
            chat_service=chat_service,
            db=db,
        )
    ]


def test_main_intent_clarification_skips_live_research(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
            confidence=0.4,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=True)
    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
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

    events = _legacy_events(_parse_events(chunks))
    assert events[0][0] == "metadata"
    assert events[0][1]["primary_task"] == "RECIPE_FIND"
    assert events[0][1]["used_live_research"] is False
    assert events[0][1]["source_count"] == 0
    assert events[1][0] == "planning"
    assert events[1][1]["primary_task"] == "RECIPE_FIND"
    assert events[1][1]["answer_strategy"] == "CLARIFICATION"
    assert events[2][0] == "message"
    assert "구체적으로" in events[2][1]["content"]
    assert events[3] == ("done", {"message_id": 123, "recipe_ids": []})
    assert live_research.build_query_calls == []
    assert live_research.research_calls == []


def test_regular_recipe_query_does_not_use_live_research(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
            confidence=0.4,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "김치랑 두부 있어",
            FakeChatService(),
        )
    )

    events = _legacy_events(_parse_events(chunks))
    assert events[0][0] == "metadata"
    assert events[0][1]["used_live_research"] is False
    assert events[0][1]["source_count"] == 0
    assert live_research.build_query_calls == []
    assert live_research.research_calls == []


def test_cooking_qa_plan_can_request_live_research(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.COOKING_QA,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    captured = {}

    class LiveCookingQAPlanner:
        async def plan(self, message, history, memory_context=None):
            return CookingQAPlan(
                sub_intent=CookingQASubIntent.GENERAL,
                question_type="GENERAL",
                rewritten_question="2026년 인기 다이어트 조리법",
                needs_live_research=True,
            )

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        captured["user_prompt"] = user_prompt
        await queue.put(("text", "최근 자료를 참고해서 답변할게요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.cooking_qa_planner",
        LiveCookingQAPlanner(),
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "요즘 인기 있는 다이어트 조리법 알려줘",
            FakeChatService(),
        )
    )

    events = _legacy_events(_parse_events(chunks))
    assert events[0][0] == "metadata"
    assert events[0][1]["used_live_research"] is True
    assert events[0][1]["source_count"] == 1
    assert live_research.build_query_calls == [
        ("2026년 인기 다이어트 조리법", PrimaryTask.COOKING_QA)
    ]
    assert "Live research evidence" in captured["user_prompt"]


def test_off_topic_query_keeps_live_research_off(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.OFF_TOPIC,
            confidence=1.0,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chunks = asyncio.run(
        _collect_stream(AgentService(), "요즘 주식 뭐 사야 돼?", FakeChatService())
    )

    events = _legacy_events(_parse_events(chunks))
    assert events[0][1]["primary_task"] == "OFF_TOPIC"
    assert events[0][1]["used_live_research"] is False
    assert events[1][0] == "planning"
    assert events[1][1]["primary_task"] == "OFF_TOPIC"
    assert events[2][0] == "message"
    assert "요리" in events[2][1]["content"]


def test_identity_query_returns_fixed_identity_message(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.IDENTITY,
            confidence=1.0,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=True)
    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )

    chunks = asyncio.run(
        _collect_stream(AgentService(), "너는 누구야?", FakeChatService())
    )

    events = _legacy_events(_parse_events(chunks))
    assert events[0][1]["primary_task"] == "IDENTITY"
    assert events[0][1]["used_live_research"] is False
    assert events[1][0] == "planning"
    assert events[1][1]["answer_strategy"] == "FIXED"
    assert events[2][0] == "message"
    assert "냉고" in events[2][1]["content"]
    assert live_research.build_query_calls == []
    assert live_research.research_calls == []


def test_recipe_query_prefetches_rag_even_when_agent_does_not_call_tool(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
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

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
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
        "app.services.agent_service.profile_update_analyzer",
        FakeProfileUpdateAnalyzer(
            ProfileUpdateDecision(
                action=ProfileUpdateAction.AUTO_SAVE,
                candidates=[
                    ProfileUpdateCandidate(
                        field="allergies",
                        operation=ProfileUpdateOperation.ADD,
                        value="새우",
                        evidence="나 새우 알레르기 있는데",
                        confidence=0.97,
                        scope="long_term",
                        subject="self",
                    )
                ],
                message="알레르기 '새우' 프로필에 저장했어요.",
            )
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "김치랑 두부 있어",
            FakeChatService(),
        )
    )

    events = _legacy_events(_parse_events(chunks))
    assert retrieval.queries[0][:2] == ("김치 두부 찌개", 3)
    assert retrieval.queries[0][2].available_ingredients == ["김치", "두부"]
    assert retrieval.queries[0][2].main_ingredients == ["김치", "두부"]
    assert "RAG recipe candidates" in captured["user_prompt"]
    assert captured["deps"].last_found_recipes[0]["id"] == 7
    evidence = next(data for name, data in events if name == "evidence")
    assert evidence["recipes"][0]["recipe_id"] == 7
    assert evidence["recipes"][0]["why_matched"] == ["김치", "두부"]
    retrieval_events = [data for name, data in events if name == "retrieval"]
    assert [event["status"] for event in retrieval_events] == [
        "started",
        "completed",
    ]
    assert ("recipes", [captured["deps"].last_found_recipes[0]]) in events
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": [7]})


def test_recipe_query_can_save_profile_side_effect_and_still_answer(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    retrieval = FakeRecipeRetrievalService()
    db = FakeDb()
    captured = {}

    class CapturingSearchPlanner:
        async def plan(
            self,
            message,
            history,
            user_profile_context=None,
            memory_context=None,
            image=None,
        ):
            captured["user_profile_context"] = user_profile_context
            captured["memory_context"] = memory_context
            return SearchPlan(
                query_text="김치 두부 찌개",
                available_ingredients=["김치", "두부"],
                main_ingredients=["김치", "두부"],
            )

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        captured["deps"] = deps
        await queue.put(("text", "새우는 피해서 추천할게요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_search_planner",
        CapturingSearchPlanner(),
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_retrieval_service",
        retrieval,
    )
    monkeypatch.setattr(
        "app.services.agent_service.profile_update_analyzer",
        FakeProfileUpdateAnalyzer(
            ProfileUpdateDecision(
                action=ProfileUpdateAction.AUTO_SAVE,
                candidates=[
                    ProfileUpdateCandidate(
                        field="allergies",
                        operation=ProfileUpdateOperation.ADD,
                        value="새우",
                        evidence="나 새우 알레르기 있는데",
                        confidence=0.97,
                        scope="long_term",
                        subject="self",
                    )
                ],
                message="알레르기 '새우' 프로필에 저장했어요.",
            )
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "나 새우 알레르기 있는데 김치랑 두부로 추천해줘",
            FakeChatService(),
            db=db,
        )
    )

    events = _legacy_events(_parse_events(chunks))
    profile_update = next(data for name, data in events if name == "profile_update")
    assert profile_update["action"] == "AUTO_SAVE"
    assert profile_update["candidates"][0]["field"] == "allergies"
    assert profile_update["candidates"][0]["value"] == "새우"
    assert db.profile.allergies == ["새우"]
    assert "새우" in captured["user_profile_context"]
    assert "새우" in captured["memory_context"]
    assert retrieval.queries[0][2].allergies == ["새우"]
    assert retrieval.queries[0][2].avoid_ingredients == ["새우"]
    evidence = next(data for name, data in events if name == "evidence")
    assert evidence["constraints"]["avoid_ingredients"] == ["새우"]
    assert any(name == "message" for name, _ in events)
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": [7]})


def test_recipe_query_skips_rag_prefetch_when_plan_does_not_require_it(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
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
        await queue.put(("text", "조금 더 조건을 알려주시면 좋아요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_search_planner",
        FakeNoRetrievalSearchPlanner(),
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
        _collect_stream(
            AgentService(),
            "뭐 먹을까?",
            FakeChatService(),
        )
    )

    events = _parse_events(chunks)
    assert retrieval.queries == []
    assert all(name != "retrieval" for name, _ in events)
    assert all(name != "evidence" for name, _ in events)
    assert "RAG recipe candidates" not in captured["user_prompt"]
    assert captured["deps"].last_found_recipes == []
    assert captured["deps"].retrieval_allowed is False
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": []})


def test_recipe_query_with_planner_clarification_ends_before_rag(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.RECIPE_FIND,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    retrieval = FakeRecipeRetrievalService()

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        raise AssertionError("clarification should not run answer agent")

    chat_service = FakeChatService()
    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.recipe_search_planner",
        FakeClarifyingSearchPlanner(),
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
        _collect_stream(
            AgentService(),
            "추천해줘",
            chat_service,
        )
    )

    all_events = _parse_events(chunks)
    events = _legacy_events(all_events)
    assert retrieval.queries == []
    assert any(
        name == "workflow"
        and data["stage"] == "completed"
        and data["status"] == "completed"
        for name, data in all_events
    )
    assert events[1][0] == "planning"
    assert events[1][1]["answer_strategy"] == "CLARIFICATION"
    assert events[1][1]["sub_intent"] == "CLARIFICATION"
    assert events[2] == (
        "message",
        {"content": "어떤 재료를 기준으로 추천해드릴까요?"},
    )
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": []})
    assert chat_service.saved[0][2] == "어떤 재료를 기준으로 추천해드릴까요?"


def test_cooking_qa_with_retrieval_uses_sub_intent_agent(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.COOKING_QA,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    retrieval = FakeRecipeRetrievalService()
    captured = {}

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        captured["agent"] = agent
        captured["user_prompt"] = user_prompt
        captured["deps"] = deps
        await queue.put(("text", "두부 대신 순두부를 써도 돼요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.cooking_qa_planner",
        FakeCookingQAPlanner(),
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
        _collect_stream(AgentService(), "두부 대신 뭐 써도 돼?", FakeChatService())
    )

    events = _parse_events(chunks)
    planning = next(data for name, data in events if name == "planning")
    assert planning["sub_intent"] == "INGREDIENT_SUBSTITUTION"
    assert planning["selected_agent"] == "ingredient_substitution_agent"
    assert retrieval.queries[0][:2] == ("두부 대신 쓸 재료", 3)
    assert retrieval.queries[0][2].main_ingredients == ["두부"]
    evidence = next(data for name, data in events if name == "evidence")
    assert evidence["recipes"][0]["recipe_id"] == 7
    assert "RAG recipe candidates" in captured["user_prompt"]
    assert captured["agent"] is ingredient_substitution_agent


def test_cooking_qa_planner_receives_memory_context(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.COOKING_QA,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)
    db = FakeDb()
    db.profile.allergies = ["새우"]
    captured = {}

    class CapturingCookingQAPlanner:
        async def plan(self, message, history, memory_context=None):
            captured["memory_context"] = memory_context
            return CookingQAPlan(
                sub_intent=CookingQASubIntent.INGREDIENT_SUBSTITUTION,
                question_type="INGREDIENT_SUBSTITUTION",
                rewritten_question="새우 없이 감칠맛 내기",
            )

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        await queue.put(("text", "새우는 피하고 표고버섯을 써보세요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.cooking_qa_planner",
        CapturingCookingQAPlanner(),
    )
    monkeypatch.setattr(
        "app.services.agent_service.profile_update_analyzer",
        FakeProfileUpdateAnalyzer(),
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(
        _collect_stream(
            AgentService(),
            "새우 대신 감칠맛 내려면 뭐 써?",
            FakeChatService(),
            db=db,
        )
    )

    events = _parse_events(chunks)
    assert "새우" in captured["memory_context"]
    assert any(name == "message" for name, _ in events)


def test_cooking_qa_clarification_stops_before_answer_agent(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.COOKING_QA,
            confidence=0.9,
            reason="테스트",
        )
    )
    live_research = FakeLiveResearchService(enabled=False)

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        raise AssertionError("clarification should not run answer agent")

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.live_research_service",
        live_research,
    )
    monkeypatch.setattr(
        "app.services.agent_service.cooking_qa_planner",
        FakeClarifyingCookingQAPlanner(),
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chat_service = FakeChatService()
    chunks = asyncio.run(
        _collect_stream(AgentService(), "그 레시피에서 뭐 빼도 돼?", chat_service)
    )

    all_events = _parse_events(chunks)
    events = _legacy_events(all_events)
    assert any(
        name == "workflow"
        and data["stage"] == "completed"
        and data["status"] == "completed"
        for name, data in all_events
    )
    assert events[1][0] == "planning"
    assert events[1][1]["primary_task"] == "COOKING_QA"
    assert events[1][1]["answer_strategy"] == "CLARIFICATION"
    assert events[1][1]["sub_intent"] == "GENERAL"
    assert events[2] == (
        "message",
        {"content": "어떤 레시피를 말씀하시는지 알려주세요?"},
    )
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": []})
    assert chat_service.saved[0][2] == "어떤 레시피를 말씀하시는지 알려주세요?"


def test_agent_service_buffers_generated_chunks_until_verification(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.SMALLTALK,
            confidence=0.95,
            reason="테스트",
        )
    )

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        await queue.put(("text", "안녕"))
        await queue.put(("text", "하세요."))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(_collect_stream(AgentService(), "안녕", FakeChatService()))

    events = _parse_events(chunks)
    workflow = [data for name, data in events if name == "workflow"]
    messages = [data["content"] for name, data in events if name == "message"]

    assert [event["stage"] for event in workflow] == [
        "classifying",
        "classifying",
        "planning",
        "planning",
        "generating",
        "generating",
        "verifying",
        "verifying",
        "completed",
    ]
    assert messages == ["안녕하세요."]
    assert events[-1] == ("done", {"message_id": 123, "recipe_ids": []})


def test_agent_service_revises_failed_answer_once_before_sending(monkeypatch):
    classifier = FakeIntentClassifier(
        MainIntentResult(
            primary_task=PrimaryTask.SMALLTALK,
            confidence=0.95,
            reason="테스트",
        )
    )
    revision_agent = object()
    calls = []

    class FakeVerifier:
        def __init__(self):
            self.calls = 0

        def verify(self, answer, recipes, memory, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    passed=False,
                    issues=["safety_answer_too_permissive"],
                )
            return SimpleNamespace(passed=True, issues=[])

    async def fake_run_agent_to_queue(queue, agent, user_prompt, history, deps):
        calls.append(agent)
        text = "수정된 안전 답변입니다." if agent is revision_agent else "괜찮아요."
        await queue.put(("text", text))
        await queue.put(("done", None))

    monkeypatch.setattr("app.services.agent_service.main_intent_classifier", classifier)
    monkeypatch.setattr(
        "app.services.agent_service.answer_verifier",
        FakeVerifier(),
    )
    monkeypatch.setattr(
        "app.services.agent_service.answer_revision_agent",
        revision_agent,
    )
    monkeypatch.setattr(
        "app.services.agent_service._run_agent_to_queue",
        fake_run_agent_to_queue,
    )

    chunks = asyncio.run(_collect_stream(AgentService(), "안녕", FakeChatService()))

    events = _parse_events(chunks)
    workflow = [data for name, data in events if name == "workflow"]
    messages = [data["content"] for name, data in events if name == "message"]

    assert messages == ["수정된 안전 답변입니다."]
    assert calls == [smalltalk_agent, revision_agent]
    assert [
        (event["stage"], event["status"], event["attempt"])
        for event in workflow
        if event["stage"] in {"revising", "verifying"}
    ] == [
        ("verifying", "started", 0),
        ("verifying", "completed", 0),
        ("revising", "started", 1),
        ("revising", "completed", 1),
        ("verifying", "started", 1),
        ("verifying", "completed", 1),
    ]
