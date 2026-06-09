from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_evals import Case, Dataset

EvalCategory = Literal[
    "recipe_find",
    "cooking_qa",
    "safety",
    "conversation",
    "profile_scope",
]


class EvalInput(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    profile: dict[str, Any] = Field(default_factory=dict)
    fixture_recipes: list[dict[str, Any]] = Field(default_factory=list)


class EvalExpected(BaseModel):
    primary_task: str
    sub_intent: str | None = None
    answer_strategy: str | None = None
    selected_agent: str | None = None
    retrieval_required: bool | None = None
    expected_recipe_ids: list[int] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    safety_sensitive: bool = False


class EvalOutput(BaseModel):
    primary_task: str
    sub_intent: str | None = None
    answer_strategy: str | None = None
    selected_agent: str | None = None
    retrieval_used: bool = False
    recipe_ids: list[int] = Field(default_factory=list)
    answer: str = ""
    verification_issues: list[str] = Field(default_factory=list)
    workflow_stages: list[str] = Field(default_factory=list)
    latency_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    judge_score: float = 5.0
    judge_reason: str | None = None
    evaluation_error: str | None = None


class AgentEvalCase(BaseModel):
    id: str
    category: EvalCategory
    inputs: EvalInput
    expected: EvalExpected
    fixture_output: EvalOutput


class AgentEvalDataset(BaseModel):
    name: str = "chat-agent-golden"
    cases: list[AgentEvalCase]

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> AgentEvalDataset:
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ValueError(f"duplicate case id: {case.id}")
            seen.add(case.id)
        return self

    def category_counts(self) -> dict[str, int]:
        return dict(Counter(case.category for case in self.cases))

    def to_pydantic_dataset(self) -> Dataset[EvalInput, EvalOutput, dict[str, Any]]:
        return Dataset(
            name=self.name,
            cases=[
                Case(
                    name=case.id,
                    inputs=case.inputs,
                    metadata={
                        "category": case.category,
                        "expected": case.expected.model_dump(mode="json"),
                        "fixture_output": case.fixture_output.model_dump(mode="json"),
                    },
                    expected_output=case.fixture_output,
                )
                for case in self.cases
            ],
        )


def load_agent_eval_dataset(path: str | Path) -> AgentEvalDataset:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return AgentEvalDataset.model_validate(payload)
