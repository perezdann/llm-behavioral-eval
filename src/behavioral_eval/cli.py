"""CLI entry point for llm-behavioral-eval."""

import argparse
from pathlib import Path

from .engine import EvaluationEngine


def main():
    parser = argparse.ArgumentParser(
        description="llm-behavioral-eval: Evaluate LLMs against behavioral specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  behavioral-eval --spec ./my-project --suite all --real-llm
  behavioral-eval --spec ./my-project --suite concrete --count 30 --real-llm --judge-provider deepseek
  behavioral-eval --spec ./my-project --suite all --real-llm --provider ollama --no-judge --repetitions 3
  behavioral-eval --spec ./my-project --suite core_principles --arena provider1 provider2
        """,
    )
    parser.add_argument(
        "--spec",
        type=Path,
        required=True,
        help="Path to spec directory (contains AGENTS.md or eval-profile.json)",
    )
    parser.add_argument(
        "--suite",
        default="all",
        choices=[
            "all",
            "core_principles",
            "rubric_dimensions",
            "roles",
            "variants",
            "concrete",
        ],
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Override test count (default: from eval-profile.json)",
    )
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Call the real LLM (otherwise simulated)",
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to llm-providers.json"
    )
    parser.add_argument(
        "--provider", default=None, help="Provider name for the model under test"
    )
    parser.add_argument(
        "--judge-provider", default=None, help="Provider for the judge/evaluator LLM"
    )
    parser.add_argument("--judge-model", default=None, help="Override judge model name")
    parser.add_argument(
        "--no-judge", action="store_true", help="Use heuristic scoring (no API cost)"
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Run each test N times, report mean +/- std dev",
    )
    parser.add_argument(
        "--heatmap",
        action="store_true",
        help="Generate per-dimension heatmap after run",
    )
    parser.add_argument(
        "--arena",
        nargs=2,
        metavar=("PROVIDER_A", "PROVIDER_B"),
        default=None,
        help="Run A/B comparison between two providers",
    )

    args = parser.parse_args()

    spec_path = args.spec.resolve()
    if not spec_path.exists():
        print(f"ERROR: Spec path not found: {spec_path}")
        return 1

    if args.arena:
        return _run_arena(args, spec_path)

    judge_prov = None if args.no_judge else args.judge_provider

    engine = EvaluationEngine(
        spec_path=spec_path,
        provider=args.provider,
        config_path=args.config,
        judge_provider=judge_prov,
        judge_model=args.judge_model,
        repetitions=args.repetitions,
        use_real_llm=args.real_llm,
    )

    mode = "REAL LLM" if args.real_llm else "SIMULATED"
    print(f"llm-behavioral-eval v1.0 ({mode})")
    print(f"Spec: {spec_path} ({engine.spec_profile.get('name', 'unknown')})")
    if args.provider:
        print(f"Provider: {args.provider}")
    if engine.judge_evaluator:
        print(f"Judge: {judge_prov} (model={engine.judge_model})")
    if args.repetitions > 1:
        print(f"Repetitions: {args.repetitions}")

    results = engine.run_suite(args.suite, args.count)
    engine.save_results(results, args.suite)

    if args.suite == "all":
        engine.print_summary(results)

    if args.heatmap and results:
        engine.generate_heatmap(results, args.suite)

    return 0


def _run_arena(args, spec_path: Path) -> int:
    """A/B comparison mode: run same tests against two providers, compute Elo-like delta."""
    import statistics

    count = args.count or 10
    print(f"Arena mode: {args.arena[0]} vs {args.arena[1]}")
    print(f"Running {count} tests per provider...")

    results_a = _run_single(args, spec_path, args.arena[0], count)
    results_b = _run_single(args, spec_path, args.arena[1], count)

    scores_a = [r.score for r in results_a]
    scores_b = [r.score for r in results_b]

    mu_a = statistics.mean(scores_a) if scores_a else 0
    mu_b = statistics.mean(scores_b) if scores_b else 0
    delta = mu_a - mu_b

    wins_a = sum(1 for a, b in zip(scores_a, scores_b) if a > b)
    wins_b = sum(1 for a, b in zip(scores_a, scores_b) if b > a)
    ties = sum(1 for a, b in zip(scores_a, scores_b) if a == b)

    from .stats import detect_difference

    diff = detect_difference(scores_a, scores_b)

    print("\n=== ARENA RESULTS ===")
    print(f"  {args.arena[0]:20s}: avg={mu_a:.2f} (n={len(scores_a)})")
    print(f"  {args.arena[1]:20s}: avg={mu_b:.2f} (n={len(scores_b)})")
    print(f"  Delta: {delta:+.2f}")
    print(
        f"  Head-to-head: {args.arena[0]} wins={wins_a}, {args.arena[1]} wins={wins_b}, ties={ties}"
    )
    print(
        f"  Significant (p<0.05): {diff.get('significant', 'N/A')} (p={diff.get('p_value', 'N/A')})"
    )

    return 0


def _run_single(args, spec_path: Path, provider: str, count: int):
    engine = EvaluationEngine(
        spec_path=spec_path,
        provider=provider,
        config_path=args.config,
        judge_provider=args.judge_provider if not args.no_judge else None,
        judge_model=args.judge_model,
        repetitions=1,
        use_real_llm=args.real_llm,
    )
    suite = "core_principles" if args.suite == "all" else args.suite
    return engine.run_suite(suite, count)


if __name__ == "__main__":
    raise SystemExit(main())
