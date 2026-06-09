from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

SAFE_FALLBACK_MESSAGE = (
    "안전한 답변을 확정하기 어려워요. 섭취는 권하지 않으며, "
    "확실한 상태 확인이나 전문가 안내를 우선해 주세요."
)


class AnswerVerifierProtocol(Protocol):
    def verify(
        self,
        answer: str,
        recipes: list[dict],
        memory: Any,
        **kwargs: Any,
    ) -> Any: ...


@dataclass(frozen=True)
class RevisionRequest:
    answer: str
    issues: list[str]
    recipes: list[dict]


@dataclass(frozen=True)
class QualityWorkflowResult:
    answer: str
    recipes: list[dict]
    revision_count: int
    used_fallback: bool
    verification: Any | None = None


StageCallback = Callable[[str, str, int], Awaitable[None]]


async def _noop_stage_callback(stage: str, status: str, attempt: int) -> None:
    return None


@dataclass(frozen=True)
class QualityWorkflowInput:
    generate: Callable[[], Awaitable[str]]
    revise: Callable[[RevisionRequest], Awaitable[str]]
    verifier: AnswerVerifierProtocol
    recipes: list[dict] = field(default_factory=list)
    memory: Any = None
    plan: Any = None
    answer_strategy: Any = None
    resolved_recipe_ids: list[int] = field(default_factory=list)
    on_stage: StageCallback = _noop_stage_callback


@dataclass
class QualityWorkflowState:
    answer: str = ""
    recipes: list[dict] = field(default_factory=list)
    revision_count: int = 0
    verification: Any | None = None


@dataclass(frozen=True)
class QualityWorkflowDeps:
    request: QualityWorkflowInput


@dataclass
class GenerateDraft(
    BaseNode[QualityWorkflowState, QualityWorkflowDeps, QualityWorkflowResult]
):
    async def run(
        self,
        ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    ) -> VerifyAnswer:
        await _emit_stage(ctx, "generating", "started")
        ctx.state.answer = await ctx.deps.request.generate()
        await _emit_stage(ctx, "generating", "completed")
        return VerifyAnswer()


@dataclass
class VerifyAnswer(
    BaseNode[QualityWorkflowState, QualityWorkflowDeps, QualityWorkflowResult]
):
    async def run(
        self,
        ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    ) -> ReviseAnswer | Complete | SafetyFallback:
        await _emit_stage(ctx, "verifying", "started")
        request = ctx.deps.request
        ctx.state.verification = request.verifier.verify(
            ctx.state.answer,
            ctx.state.recipes,
            request.memory,
            plan=request.plan,
            answer_strategy=request.answer_strategy,
            resolved_recipe_ids=request.resolved_recipe_ids,
        )
        await _emit_stage(ctx, "verifying", "completed")
        if ctx.state.verification.passed:
            return Complete()
        ctx.state.recipes = _filter_conflicting_recipes(
            ctx.state.recipes,
            ctx.state.verification.issues,
        )
        if ctx.state.revision_count >= 1:
            return SafetyFallback()
        return ReviseAnswer()


@dataclass
class ReviseAnswer(
    BaseNode[QualityWorkflowState, QualityWorkflowDeps, QualityWorkflowResult]
):
    async def run(
        self,
        ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    ) -> VerifyAnswer:
        await _emit_stage(ctx, "revising", "started", attempt=1)
        ctx.state.revision_count = 1
        ctx.state.answer = await ctx.deps.request.revise(
            RevisionRequest(
                answer=ctx.state.answer,
                issues=list(ctx.state.verification.issues),
                recipes=list(ctx.state.recipes),
            )
        )
        await _emit_stage(ctx, "revising", "completed", attempt=1)
        return VerifyAnswer()


@dataclass
class SafetyFallback(
    BaseNode[QualityWorkflowState, QualityWorkflowDeps, QualityWorkflowResult]
):
    async def run(
        self,
        ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    ) -> End[QualityWorkflowResult]:
        ctx.state.answer = SAFE_FALLBACK_MESSAGE
        ctx.state.recipes = []
        await _emit_stage(ctx, "completed", "completed")
        return End(_result(ctx, used_fallback=True))


@dataclass
class Complete(
    BaseNode[QualityWorkflowState, QualityWorkflowDeps, QualityWorkflowResult]
):
    async def run(
        self,
        ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    ) -> End[QualityWorkflowResult]:
        await _emit_stage(ctx, "completed", "completed")
        return End(_result(ctx, used_fallback=False))


def _result(
    ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    *,
    used_fallback: bool,
) -> QualityWorkflowResult:
    return QualityWorkflowResult(
        answer=ctx.state.answer,
        recipes=list(ctx.state.recipes),
        revision_count=ctx.state.revision_count,
        used_fallback=used_fallback,
        verification=ctx.state.verification,
    )


async def _emit_stage(
    ctx: GraphRunContext[QualityWorkflowState, QualityWorkflowDeps],
    stage: str,
    status: str,
    *,
    attempt: int | None = None,
) -> None:
    await ctx.deps.request.on_stage(
        stage,
        status,
        ctx.state.revision_count if attempt is None else attempt,
    )


def _filter_conflicting_recipes(
    recipes: list[dict],
    issues: list[str],
) -> list[dict]:
    blocked_values = [
        value
        for issue in issues
        if (
            value := _issue_value(
                issue,
                "recipe_contains_allergy:",
                "recipe_contains_avoid_ingredient:",
                "answer_recipe_conflict_avoid_ingredient:",
            )
        )
    ]
    if not blocked_values:
        return list(recipes)
    return [
        recipe
        for recipe in recipes
        if not any(_recipe_contains(recipe, value) for value in blocked_values)
    ]


def _issue_value(issue: str, *prefixes: str) -> str | None:
    for prefix in prefixes:
        if issue.startswith(prefix):
            return issue.removeprefix(prefix).strip() or None
    return None


def _recipe_contains(recipe: dict, value: str) -> bool:
    parts = [
        str(recipe.get("title") or ""),
        str(recipe.get("summary") or ""),
        str(recipe.get("description") or ""),
    ]
    ingredients = recipe.get("ingredients")
    if isinstance(ingredients, list):
        parts.extend(str(item) for item in ingredients)
    normalized_value = "".join(value.lower().split())
    return any(
        normalized_value in "".join(part.lower().split())
        for part in parts
        if normalized_value
    )


quality_graph = Graph(
    nodes=[GenerateDraft, VerifyAnswer, ReviseAnswer, SafetyFallback, Complete],
    state_type=QualityWorkflowState,
    run_end_type=QualityWorkflowResult,
)


class AgentQualityWorkflow:
    async def run(self, request: QualityWorkflowInput) -> QualityWorkflowResult:
        result = await quality_graph.run(
            GenerateDraft(),
            state=QualityWorkflowState(recipes=list(request.recipes)),
            deps=QualityWorkflowDeps(request=request),
        )
        return result.output
