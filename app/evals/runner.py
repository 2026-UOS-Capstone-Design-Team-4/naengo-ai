from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal

from app.evals.baseline import BaselineComparison, compare_with_baseline
from app.evals.dataset import (
    AgentEvalCase,
    EvalInput,
    EvalOutput,
    load_agent_eval_dataset,
)

EvalMode = Literal["deterministic", "live", "retrieval"]


@dataclass(frozen=True)
class EvalRunConfig:
    mode: EvalMode
    dataset_path: str | Path
    output_dir: str | Path
    baseline_path: str | Path | None = None
    case_id: str | None = None
    with_db: bool = False
    update_baseline: bool = False


@dataclass(frozen=True)
class EvalRunResult:
    passed: bool
    case_count: int
    metrics: dict[str, float | int]
    case_results: list[dict]
    comparison: BaselineComparison
    json_path: Path
    markdown_path: Path


@dataclass
class AgentEvalRunner:
    output_provider: Callable[[AgentEvalCase], EvalOutput] | None = None

    def run(self, config: EvalRunConfig) -> EvalRunResult:
        dataset = load_agent_eval_dataset(config.dataset_path)
        cases = self._selected_cases(dataset.cases, config.case_id)
        outputs = self._run_pydantic_evals(dataset, cases)
        case_results = [_evaluate_case(case, outputs[case.id]) for case in cases]
        metrics = _aggregate_metrics(case_results)
        comparison = self._compare(config, metrics)
        json_path, markdown_path = _write_reports(
            config=config,
            metrics=metrics,
            case_results=case_results,
            comparison=comparison,
        )
        if config.update_baseline:
            self._update_baseline(config, metrics)
        return EvalRunResult(
            passed=comparison.passed,
            case_count=len(cases),
            metrics=metrics,
            case_results=case_results,
            comparison=comparison,
            json_path=json_path,
            markdown_path=markdown_path,
        )

    def _selected_cases(
        self,
        cases: list[AgentEvalCase],
        case_id: str | None,
    ) -> list[AgentEvalCase]:
        if case_id is None:
            return cases
        selected = [case for case in cases if case.id == case_id]
        if not selected:
            raise ValueError(f"unknown case id: {case_id}")
        return selected

    def _run_pydantic_evals(
        self,
        dataset,
        cases: list[AgentEvalCase],
    ) -> dict[str, EvalOutput]:
        selected_ids = {case.id for case in cases}
        selected_dataset = dataset.model_copy(
            update={
                "cases": [case for case in dataset.cases if case.id in selected_ids]
            }
        )
        pydantic_dataset = selected_dataset.to_pydantic_dataset()
        outputs_by_message = {
            case.inputs.message: (
                self.output_provider(case)
                if self.output_provider is not None
                else case.fixture_output
            )
            for case in cases
        }

        def task(inputs: EvalInput) -> EvalOutput:
            return outputs_by_message[inputs.message]

        asyncio.run(pydantic_dataset.evaluate(task, progress=False))
        return {case.id: outputs_by_message[case.inputs.message] for case in cases}

    def _compare(
        self,
        config: EvalRunConfig,
        metrics: dict[str, float | int],
    ) -> BaselineComparison:
        if config.case_id is not None or config.baseline_path is None:
            return compare_with_baseline(metrics, {})
        payload = json.loads(Path(config.baseline_path).read_text(encoding="utf-8"))
        return compare_with_baseline(metrics, payload["metrics"])

    def _update_baseline(
        self,
        config: EvalRunConfig,
        metrics: dict[str, float | int],
    ) -> None:
        if config.baseline_path is None:
            raise ValueError("--update-baseline requires --baseline")
        payload = {
            "schema_version": 1,
            "dataset": Path(config.dataset_path).stem,
            "mode": config.mode,
            "updated_at": datetime.now(UTC).isoformat(),
            "metrics": metrics,
        }
        Path(config.baseline_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _evaluate_case(case: AgentEvalCase, output: EvalOutput) -> dict:
    started = perf_counter()
    expected = case.expected
    intent_passed = output.primary_task == expected.primary_task
    routing_passed = (
        expected.selected_agent is None
        or output.selected_agent == expected.selected_agent
    )
    retrieval_passed = _retrieval_passed(case, output)
    safety_violations = _safety_violations(case, output)
    return {
        "case_id": case.id,
        "category": case.category,
        "intent_passed": intent_passed,
        "routing_passed": routing_passed,
        "routing_applicable": expected.selected_agent is not None,
        "retrieval_passed": retrieval_passed,
        "retrieval_applicable": expected.retrieval_required is not None,
        "safety_violations": safety_violations,
        "judge_score": output.judge_score,
        "judge_reason": output.judge_reason,
        "evaluation_error": output.evaluation_error,
        "latency_ms": output.latency_ms or (perf_counter() - started) * 1000,
        "total_tokens": output.input_tokens + output.output_tokens,
        "output": output.model_dump(mode="json"),
    }


def _retrieval_passed(case: AgentEvalCase, output: EvalOutput) -> bool:
    expected = case.expected
    if expected.retrieval_required is None:
        return True
    if output.retrieval_used != expected.retrieval_required:
        return False
    return set(expected.expected_recipe_ids).issubset(output.recipe_ids)


def _safety_violations(case: AgentEvalCase, output: EvalOutput) -> int:
    issue_prefixes = (
        "recipe_contains_allergy:",
        "recipe_contains_avoid_ingredient:",
        "answer_recipe_conflict_avoid_ingredient:",
        "safety_answer_too_permissive",
    )
    return sum(issue.startswith(issue_prefixes) for issue in output.verification_issues)


def _aggregate_metrics(case_results: list[dict]) -> dict[str, float | int]:
    count = len(case_results)
    routing = [case for case in case_results if case["routing_applicable"]]
    retrieval = [case for case in case_results if case["retrieval_applicable"]]
    judge_scores = [float(case["judge_score"]) for case in case_results]
    return {
        "safety_violations": sum(
            int(case["safety_violations"]) for case in case_results
        ),
        "evaluation_errors": sum(
            bool(case["evaluation_error"]) for case in case_results
        ),
        "intent_accuracy": _ratio(
            sum(bool(case["intent_passed"]) for case in case_results),
            count,
        ),
        "routing_accuracy": _ratio(
            sum(bool(case["routing_passed"]) for case in routing),
            len(routing),
        ),
        "retrieval_accuracy": _ratio(
            sum(bool(case["retrieval_passed"]) for case in retrieval),
            len(retrieval),
        ),
        "judge_average": sum(judge_scores) / count if count else 0,
        "judge_below_three": sum(score < 3 for score in judge_scores),
        "latency_ms": sum(float(case["latency_ms"]) for case in case_results),
        "total_tokens": sum(int(case["total_tokens"]) for case in case_results),
    }


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _write_reports(
    *,
    config: EvalRunConfig,
    metrics: dict[str, float | int],
    case_results: list[dict],
    comparison: BaselineComparison,
) -> tuple[Path, Path]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"agent-eval-{config.mode}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    payload = {
        "schema_version": 1,
        "mode": config.mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": comparison.passed,
        "metrics": metrics,
        "failures": comparison.failures,
        "warnings": comparison.warnings,
        "cases": case_results,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown_report(payload), encoding="utf-8")
    return json_path, markdown_path


def _markdown_report(payload: dict) -> str:
    metrics = payload["metrics"]
    lines = [
        "# Agent Evaluation Report",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Cases: `{len(payload['cases'])}`",
        f"- Intent accuracy: `{metrics['intent_accuracy']:.4f}`",
        f"- Routing accuracy: `{metrics['routing_accuracy']:.4f}`",
        f"- Retrieval accuracy: `{metrics['retrieval_accuracy']:.4f}`",
        f"- Safety violations: `{metrics['safety_violations']}`",
        f"- Evaluation errors: `{metrics['evaluation_errors']}`",
        f"- Judge average: `{metrics['judge_average']:.2f}`",
    ]
    if payload["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in payload["failures"])
    if payload["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    return "\n".join(lines) + "\n"
