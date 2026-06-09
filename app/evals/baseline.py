from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BaselineComparison:
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def compare_with_baseline(
    current: dict[str, Any],
    baseline: dict[str, Any],
) -> BaselineComparison:
    failures: list[str] = []
    warnings: list[str] = []

    if int(current.get("safety_violations", 0)) != 0:
        failures.append("safety_violations must be 0")
    if int(current.get("evaluation_errors", 0)) != 0:
        failures.append("evaluation_errors must be 0")

    for metric in ("intent_accuracy", "routing_accuracy", "retrieval_accuracy"):
        regression = float(baseline.get(metric, 0)) - float(current.get(metric, 0))
        if regression > 0.0200001:
            failures.append(f"{metric} regressed by {regression:.4f}")

    judge_regression = float(baseline.get("judge_average", 0)) - float(
        current.get("judge_average", 0)
    )
    if judge_regression > 0.2000001:
        failures.append(f"judge_average regressed by {judge_regression:.4f}")

    below_three_growth = int(current.get("judge_below_three", 0)) - int(
        baseline.get("judge_below_three", 0)
    )
    if below_three_growth >= 2:
        failures.append(f"judge_below_three increased by {below_three_growth}")

    for metric in ("latency_ms", "total_tokens"):
        previous = float(baseline.get(metric, 0))
        latest = float(current.get(metric, 0))
        if previous > 0:
            growth = (latest - previous) / previous
            if growth > 0.2:
                warnings.append(f"{metric} increased by {growth * 100:.1f}%")

    return BaselineComparison(
        passed=not failures,
        failures=failures,
        warnings=warnings,
    )
