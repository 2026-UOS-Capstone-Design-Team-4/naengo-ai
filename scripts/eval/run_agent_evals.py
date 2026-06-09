from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evals.runner import AgentEvalRunner, EvalRunConfig  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Naengo agent evaluations.")
    parser.add_argument(
        "--mode",
        choices=("deterministic", "live", "retrieval"),
        default="deterministic",
    )
    parser.add_argument(
        "--dataset",
        default="evals/cases/chat_agent.yaml",
    )
    parser.add_argument("--case")
    parser.add_argument("--output", default="artifacts/evals")
    parser.add_argument("--baseline")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--with-db", action="store_true")
    parser.add_argument("--judge-model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "retrieval" and not args.with_db:
        raise SystemExit("retrieval mode requires --with-db")

    baseline = args.baseline
    if baseline is None and args.mode == "deterministic":
        baseline = "evals/baselines/deterministic.json"

    output_provider = None
    if args.mode == "live":
        from app.evals.live import LiveAgentOutputProvider

        output_provider = LiveAgentOutputProvider(judge_model=args.judge_model)
    elif args.mode == "retrieval":
        from app.evals.retrieval import RetrievalOutputProvider

        output_provider = RetrievalOutputProvider()

    result = AgentEvalRunner(output_provider=output_provider).run(
        EvalRunConfig(
            mode=args.mode,
            dataset_path=args.dataset,
            baseline_path=baseline,
            output_dir=args.output,
            case_id=args.case,
            with_db=args.with_db,
            update_baseline=args.update_baseline,
        )
    )
    sys.stdout.write(f"cases={result.case_count} passed={result.passed}\n")
    sys.stdout.write(f"json={result.json_path}\n")
    sys.stdout.write(f"markdown={result.markdown_path}\n")
    for failure in result.comparison.failures:
        sys.stderr.write(f"failure: {failure}\n")
    for warning in result.comparison.warnings:
        sys.stderr.write(f"warning: {warning}\n")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
