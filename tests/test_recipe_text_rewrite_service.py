from types import SimpleNamespace

import pytest

from app.models.recipe_source import (
    RecipeSourceExtractedIngredient,
    RecipeSourceExtractedStep,
    RecipeSourceExtraction,
)
from app.services.ingestion.recipe_text_rewrite_service import (
    AIRecipeTextRewriter,
    RecipeRewriteOutput,
    RecipeTextRewriteError,
    StepRewriteOutput,
    draft_from_extraction,
)


class FakeAgent:
    def __init__(self, output: RecipeRewriteOutput | Exception):
        self.output = output
        self.prompt = None

    def run_sync(self, prompt: str):
        self.prompt = prompt
        if isinstance(self.output, Exception):
            raise self.output
        return SimpleNamespace(output=self.output)


def make_extraction() -> RecipeSourceExtraction:
    extraction = RecipeSourceExtraction(
        title="원문식 김치찌개",
        summary="원문 요약",
        description="원문 설명",
        servings=2,
        cooking_time_minutes=20,
        difficulty="easy",
    )
    extraction.ingredients = [
        RecipeSourceExtractedIngredient(
            name="김치",
            normalized_name="김치",
            amount_text="200g",
            raw_text="김치 200g 넣어주세요",
            sort_order=1,
        )
    ]
    extraction.steps = [
        RecipeSourceExtractedStep(
            step_no=1,
            instruction="김치를 팬에 넣고 볶아주세요.",
            tip="원문 팁",
            source_image_url="https://example.com/step.jpg",
            sort_order=1,
        )
    ]
    return extraction


def test_ai_rewriter_returns_naengo_style_draft_and_preserves_structural_fields():
    agent = FakeAgent(
        RecipeRewriteOutput(
            title="담백하게 끓이는 김치찌개",
            summary="김치의 맛을 살린 기본 찌개입니다.",
            description="잘 익은 김치를 먼저 볶아 깊은 맛을 냅니다.",
            steps=[
                StepRewriteOutput(
                    title="김치 볶기",
                    instruction="냄비에 김치를 넣고 숨이 살짝 죽을 때까지 볶습니다.",
                    tip="중불에서 천천히 볶으면 맛이 더 부드럽습니다.",
                )
            ],
        )
    )
    rewriter = AIRecipeTextRewriter(agent=agent, model="test-model")

    draft = rewriter.rewrite(make_extraction())

    assert draft.title == "담백하게 끓이는 김치찌개"
    assert draft.ingredients[0].raw_text == "김치 200g 넣어주세요"
    assert draft.ingredients[0].normalized_name == "김치"
    assert draft.steps[0].instruction == (
        "냄비에 김치를 넣고 숨이 살짝 죽을 때까지 볶습니다."
    )
    assert draft.steps[0].source_image_url == "https://example.com/step.jpg"
    assert '"title": "원문식 김치찌개"' in agent.prompt


def test_ai_rewriter_rejects_mismatched_step_count():
    agent = FakeAgent(
        RecipeRewriteOutput(
            title="새 제목",
            summary="새 요약",
            description="새 설명",
            steps=[],
        )
    )
    rewriter = AIRecipeTextRewriter(agent=agent, model="test-model")

    with pytest.raises(RecipeTextRewriteError):
        rewriter.rewrite(make_extraction())


def test_ai_rewriter_builds_agent_with_import_timeout(monkeypatch):
    calls = []

    def build_agent(model, timeout_seconds):
        calls.append((model, timeout_seconds))
        return FakeAgent(
            RecipeRewriteOutput(
                title="새 제목",
                summary="새 요약",
                description="새 설명",
                steps=[StepRewriteOutput(instruction="새 단계")],
            )
        )

    monkeypatch.setattr(
        "app.services.ingestion.recipe_text_rewrite_service._build_agent",
        build_agent,
    )

    rewriter = AIRecipeTextRewriter(model="test-model", timeout_seconds=12.5)

    assert rewriter.timeout_seconds == 12.5
    assert calls == [("test-model", 12.5)]


def test_draft_from_extraction_keeps_original_as_passthrough_shape():
    extraction = make_extraction()

    draft = draft_from_extraction(extraction)

    assert draft.title == extraction.title
    assert draft.description == extraction.description
    assert draft.ingredients[0].raw_text == "김치 200g 넣어주세요"
    assert draft.steps[0].instruction == "김치를 팬에 넣고 볶아주세요."
