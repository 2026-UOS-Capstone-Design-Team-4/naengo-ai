import asyncio
from types import SimpleNamespace

from app.agents.workflow.quality import (
    AgentQualityWorkflow,
    QualityWorkflowInput,
)


class SequencedVerifier:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def verify(self, answer, recipes, memory, **kwargs):
        self.calls.append((answer, list(recipes), kwargs))
        return self.results.pop(0)


def test_quality_workflow_returns_first_verified_draft_without_revision():
    verifier = SequencedVerifier([SimpleNamespace(passed=True, issues=[])])
    revisions = []
    stages = []

    async def generate():
        return "검증된 초안입니다."

    async def revise(request):
        revisions.append(request)
        return "호출되면 안 됩니다."

    async def on_stage(stage, status, attempt):
        stages.append((stage, status, attempt))

    result = asyncio.run(
        AgentQualityWorkflow().run(
            QualityWorkflowInput(
                generate=generate,
                revise=revise,
                verifier=verifier,
                recipes=[{"id": 1, "title": "두부 볶음"}],
                on_stage=on_stage,
            )
        )
    )

    assert result.answer == "검증된 초안입니다."
    assert result.recipes == [{"id": 1, "title": "두부 볶음"}]
    assert result.revision_count == 0
    assert result.used_fallback is False
    assert revisions == []
    assert stages == [
        ("generating", "started", 0),
        ("generating", "completed", 0),
        ("verifying", "started", 0),
        ("verifying", "completed", 0),
        ("completed", "completed", 0),
    ]


def test_quality_workflow_revises_once_after_filtering_conflicting_recipe():
    verifier = SequencedVerifier(
        [
            SimpleNamespace(
                passed=False,
                issues=["recipe_contains_allergy:새우"],
            ),
            SimpleNamespace(passed=True, issues=[]),
        ]
    )
    revisions = []

    async def generate():
        return "새우 볶음밥을 추천해요."

    async def revise(request):
        revisions.append(request)
        return "알레르기 조건에 맞는 다른 요리를 안내해드릴게요."

    result = asyncio.run(
        AgentQualityWorkflow().run(
            QualityWorkflowInput(
                generate=generate,
                revise=revise,
                verifier=verifier,
                recipes=[
                    {
                        "id": 1,
                        "title": "새우 볶음밥",
                        "ingredients": [{"name": "새우"}],
                    },
                    {
                        "id": 2,
                        "title": "두부 볶음",
                        "ingredients": [{"name": "두부"}],
                    },
                ],
            )
        )
    )

    assert result.answer == "알레르기 조건에 맞는 다른 요리를 안내해드릴게요."
    assert result.recipes == [
        {
            "id": 2,
            "title": "두부 볶음",
            "ingredients": [{"name": "두부"}],
        }
    ]
    assert result.revision_count == 1
    assert result.used_fallback is False
    assert revisions[0].issues == ["recipe_contains_allergy:새우"]
    assert revisions[0].recipes == result.recipes
    assert len(verifier.calls) == 2


def test_quality_workflow_uses_safe_fallback_after_failed_revision():
    verifier = SequencedVerifier(
        [
            SimpleNamespace(passed=False, issues=["safety_answer_too_permissive"]),
            SimpleNamespace(passed=False, issues=["safety_answer_too_permissive"]),
        ]
    )
    revision_calls = 0

    async def generate():
        return "먹어도 돼요."

    async def revise(request):
        nonlocal revision_calls
        revision_calls += 1
        return "그래도 괜찮아요."

    result = asyncio.run(
        AgentQualityWorkflow().run(
            QualityWorkflowInput(
                generate=generate,
                revise=revise,
                verifier=verifier,
                recipes=[{"id": 1, "title": "의심되는 음식"}],
            )
        )
    )

    assert result.answer == (
        "안전한 답변을 확정하기 어려워요. 섭취는 권하지 않으며, "
        "확실한 상태 확인이나 전문가 안내를 우선해 주세요."
    )
    assert result.recipes == []
    assert result.revision_count == 1
    assert result.used_fallback is True
    assert revision_calls == 1
