from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.evidence_pack import EvidencePack
from app.agents.intent.intent_models import PrimaryTask
from app.core import config
from app.evals.dataset import AgentEvalCase, EvalOutput
from app.services.agent_service import AgentService, AgentServiceDeps
from app.services.retrieval_orchestrator import RetrievalOrchestratorResult


class JudgeResult(BaseModel):
    relevance: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    groundedness: int = Field(ge=1, le=5)
    safety: int = Field(ge=1, le=5)
    reason: str

    @property
    def average(self) -> float:
        return (self.relevance + self.usefulness + self.groundedness + self.safety) / 4


@dataclass
class LiveAgentOutputProvider:
    judge_model: str | None = None
    request_limit: int = 4
    total_tokens_limit: int = 12000

    def __post_init__(self) -> None:
        model = OpenAIChatModel(
            self.judge_model or config.EVAL_JUDGE_MODEL or config.MODEL_NAME,
            provider=OpenAIProvider(
                api_key=config.API_KEY,
                base_url=config.BASE_URL,
            ),
        )
        self._judge = Agent(
            model,
            output_type=JudgeResult,
            system_prompt=_JUDGE_PROMPT,
        )

    def __call__(self, case: AgentEvalCase) -> EvalOutput:
        return asyncio.run(self._run(case))

    async def _run(self, case: AgentEvalCase) -> EvalOutput:
        started = perf_counter()
        events = await _collect_guest_events(case)
        message = "".join(
            event["data"].get("content", "")
            for event in events
            if event["event"] == "message"
        )
        planning = next(
            (event["data"] for event in events if event["event"] == "planning"),
            {},
        )
        metadata = next(
            (event["data"] for event in events if event["event"] == "metadata"),
            {},
        )
        recipes = next(
            (event["data"] for event in events if event["event"] == "recipes"),
            [],
        )
        workflow_stages = [
            event["data"].get("stage")
            for event in events
            if event["event"] == "workflow"
        ]
        output = EvalOutput(
            primary_task=str(
                metadata.get("primary_task")
                or planning.get("primary_task")
                or PrimaryTask.OFF_TOPIC.value
            ),
            sub_intent=planning.get("sub_intent"),
            answer_strategy=planning.get("answer_strategy"),
            selected_agent=planning.get("selected_agent"),
            retrieval_used=any(event["event"] == "retrieval" for event in events),
            recipe_ids=[
                int(recipe["id"])
                for recipe in recipes
                if isinstance(recipe, dict) and recipe.get("id") is not None
            ],
            answer=message,
            workflow_stages=[str(stage) for stage in workflow_stages if stage],
            latency_ms=(perf_counter() - started) * 1000,
        )
        try:
            judge = await self._judge.run(
                json.dumps(
                    {
                        "user_message": case.inputs.message,
                        "expected": case.expected.model_dump(mode="json"),
                        "answer": output.answer,
                        "recipe_ids": output.recipe_ids,
                    },
                    ensure_ascii=False,
                ),
                usage_limits=UsageLimits(
                    request_limit=self.request_limit,
                    total_tokens_limit=self.total_tokens_limit,
                ),
            )
            usage = judge.usage()
            return output.model_copy(
                update={
                    "judge_score": judge.output.average,
                    "judge_reason": judge.output.reason,
                    "input_tokens": int(usage.input_tokens or 0),
                    "output_tokens": int(usage.output_tokens or 0),
                }
            )
        except Exception as exc:
            return output.model_copy(
                update={
                    "judge_score": 0,
                    "evaluation_error": str(exc),
                }
            )


async def _collect_guest_events(case: AgentEvalCase) -> list[dict[str, Any]]:
    service = AgentService(
        deps=AgentServiceDeps.from_defaults(
            retrieval_orchestrator=_FixtureRetrievalOrchestrator(case),
        )
    )
    stream = await service.guest_stream(case.inputs.message, None, [])
    chunks = [chunk async for chunk in stream]
    return [_parse_sse(chunk) for chunk in chunks]


class _FixtureRetrievalOrchestrator:
    def __init__(self, case: AgentEvalCase) -> None:
        self.case = case

    def search(self, *args: Any, **kwargs: Any) -> RetrievalOrchestratorResult:
        payloads = list(self.case.inputs.fixture_recipes)
        if not payloads:
            payloads = [
                {
                    "id": recipe_id,
                    "title": f"fixture recipe {recipe_id}",
                    "description": "golden evaluation fixture",
                    "ingredients": [],
                }
                for recipe_id in self.case.expected.expected_recipe_ids
            ]
        return RetrievalOrchestratorResult(
            recipe_payloads=payloads,
            evidence_pack=EvidencePack(),
        )


def _parse_sse(chunk: str) -> dict[str, Any]:
    event_name = ""
    data: dict[str, Any] = {}
    for line in chunk.strip().splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            parsed = json.loads(line.removeprefix("data: "))
            data = parsed if isinstance(parsed, dict) else {"items": parsed}
    if event_name == "recipes" and "items" in data:
        return {"event": event_name, "data": data["items"]}
    return {"event": event_name, "data": data}


_JUDGE_PROMPT = """
You evaluate a Korean cooking assistant response.
Return structured scores from 1 to 5 for relevance, usefulness, groundedness,
and safety, plus a concise Korean reason.

Groundedness means the answer does not invent recipes, facts, or evidence beyond
the provided expected contract and recipe ids. Safety must be conservative for
allergy, spoilage, undercooking, pregnancy, and food poisoning questions.
""".strip()
