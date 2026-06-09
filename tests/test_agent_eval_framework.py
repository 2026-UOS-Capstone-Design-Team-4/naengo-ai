import json

import pytest

from app.evals.baseline import BaselineComparison, compare_with_baseline
from app.evals.dataset import (
    AgentEvalCase,
    AgentEvalDataset,
    EvalExpected,
    EvalInput,
    EvalOutput,
    load_agent_eval_dataset,
)
from app.evals.runner import AgentEvalRunner, EvalRunConfig


def _case(case_id: str, category: str = "recipe_find") -> AgentEvalCase:
    return AgentEvalCase(
        id=case_id,
        category=category,
        inputs=EvalInput(message="김치랑 두부 있어"),
        expected=EvalExpected(
            primary_task="RECIPE_FIND",
            selected_agent="recipe_agent",
        ),
        fixture_output=EvalOutput(
            primary_task="RECIPE_FIND",
            selected_agent="recipe_agent",
        ),
    )


def test_dataset_rejects_duplicate_case_ids():
    with pytest.raises(ValueError, match="duplicate case id"):
        AgentEvalDataset(cases=[_case("same"), _case("same")])


def test_golden_dataset_has_50_balanced_cases():
    dataset = load_agent_eval_dataset("evals/cases/chat_agent.yaml")

    assert len(dataset.cases) == 50
    assert dataset.category_counts() == {
        "recipe_find": 15,
        "cooking_qa": 15,
        "safety": 10,
        "conversation": 5,
        "profile_scope": 5,
    }


def test_baseline_comparison_fails_on_any_safety_violation():
    result = compare_with_baseline(
        current={
            "safety_violations": 1,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
        },
        baseline={
            "safety_violations": 0,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
        },
    )

    assert result.passed is False
    assert "safety_violations must be 0" in result.failures


def test_baseline_comparison_fails_on_evaluation_error():
    result = compare_with_baseline(
        current={
            "safety_violations": 0,
            "evaluation_errors": 1,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
        },
        baseline={},
    )

    assert result.passed is False
    assert "evaluation_errors must be 0" in result.failures


def test_baseline_comparison_applies_accuracy_and_judge_tolerances():
    result = compare_with_baseline(
        current={
            "safety_violations": 0,
            "intent_accuracy": 0.97,
            "routing_accuracy": 0.98,
            "retrieval_accuracy": 0.99,
            "judge_average": 4.7,
            "judge_below_three": 3,
        },
        baseline={
            "safety_violations": 0,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
        },
    )

    assert result == BaselineComparison(
        passed=False,
        failures=[
            "intent_accuracy regressed by 0.0300",
            "judge_average regressed by 0.3000",
            "judge_below_three increased by 3",
        ],
        warnings=[],
    )


def test_baseline_comparison_warns_on_latency_and_token_growth():
    result = compare_with_baseline(
        current={
            "safety_violations": 0,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
            "latency_ms": 1250,
            "total_tokens": 1300,
        },
        baseline={
            "safety_violations": 0,
            "intent_accuracy": 1.0,
            "routing_accuracy": 1.0,
            "retrieval_accuracy": 1.0,
            "judge_average": 5.0,
            "judge_below_three": 0,
            "latency_ms": 1000,
            "total_tokens": 1000,
        },
    )

    assert result.passed is True
    assert result.warnings == [
        "latency_ms increased by 25.0%",
        "total_tokens increased by 30.0%",
    ]


def test_baseline_file_is_valid_json():
    payload = json.loads(
        open(
            "evals/baselines/deterministic.json",
            encoding="utf-8",
        ).read()
    )

    assert payload["schema_version"] == 1
    assert payload["metrics"]["safety_violations"] == 0


def test_deterministic_runner_generates_json_and_markdown_reports(tmp_path):
    result = AgentEvalRunner().run(
        EvalRunConfig(
            mode="deterministic",
            dataset_path="evals/cases/chat_agent.yaml",
            baseline_path="evals/baselines/deterministic.json",
            output_dir=tmp_path,
        )
    )

    assert result.passed is True
    assert result.case_count == 50
    assert result.metrics["intent_accuracy"] == 1.0
    assert result.metrics["routing_accuracy"] == 1.0
    assert result.metrics["retrieval_accuracy"] == 1.0
    assert result.metrics["safety_violations"] == 0
    assert result.json_path.exists()
    assert result.markdown_path.exists()
    assert "Agent Evaluation Report" in result.markdown_path.read_text(encoding="utf-8")


def test_runner_can_filter_a_single_case(tmp_path):
    result = AgentEvalRunner().run(
        EvalRunConfig(
            mode="deterministic",
            dataset_path="evals/cases/chat_agent.yaml",
            output_dir=tmp_path,
            case_id="sf01",
        )
    )

    assert result.case_count == 1
    assert result.case_results[0]["case_id"] == "sf01"
