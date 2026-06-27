"""Report generation: JSON, Markdown, heatmaps, with confidence intervals."""

import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .types import TestResult
from .stats import confidence_interval


def generate_report(
    results: List[TestResult],
    suite: str,
    provider_name: str,
    provider_model: str,
    report_dir: Path,
    judge_provider: str = None,
    judge_model: str = None,
    repetitions: int = 1,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    provider = provider_name.replace("/", "-")
    report_dir.mkdir(parents=True, exist_ok=True)

    n = len(results)
    scores = [r.score for r in results]
    avg = statistics.mean(scores) if n else 0
    passed = sum(1 for r in results if r.passed)
    total_time = sum(r.time_seconds for r in results)

    # Confidence interval
    if n >= 2:
        ci_mean, ci_low, ci_high = confidence_interval(scores)
    else:
        ci_mean, ci_low, ci_high = avg, avg, avg

    # Per-dimension judge scores aggregate
    dim_scores: Dict[str, List[float]] = {}
    for r in results:
        js = getattr(r, "judge_scores", None) or {}
        for dim, val in js.items():
            dim_scores.setdefault(dim, []).append(val)

    dim_summary = {}
    for dim, vals in dim_scores.items():
        if vals:
            dim_summary[dim] = {
                "avg": round(statistics.mean(vals), 2),
                "stdev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0,
            }

    report_data = {
        "timestamp": timestamp,
        "provider": provider,
        "suite": suite,
        "total_tests": n,
        "passed": passed,
        "average_score": round(avg, 2),
        "confidence_interval_95": [round(ci_low, 2), round(ci_high, 2)],
        "repetitions": repetitions,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "dimension_summary": dim_summary,
        "results": [_serialize_result(r) for r in results],
        "config_used": {
            "provider": provider,
            "model": provider_model,
        },
    }

    json_path = report_dir / f"{timestamp}-{provider}-{suite}.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # Markdown summary
    md_path = report_dir / f"{timestamp}-{provider}-{suite}.md"
    avg_time = total_time / n if n else 0
    judge_info = f" | Judge: {judge_provider}/{judge_model}" if judge_provider else ""
    with open(md_path, "w") as f:
        f.write(f"# Test Report - {suite}\n\n")
        f.write(f"**Provider**: {provider} ({provider_model}){judge_info}\n")
        f.write(f"**Date**: {timestamp}\n")
        f.write(f"**Tests**: {n} | **Passed**: {passed} | **Avg Score**: {avg:.2f} [95% CI: {ci_low:.2f}-{ci_high:.2f}]\n")
        if repetitions > 1:
            avg_std = statistics.mean([r.std_dev for r in results if r.std_dev > 0]) if n else 0
            f.write(f"**Repetitions**: {repetitions} | **Avg Std Dev**: {avg_std:.2f}\n")
        f.write(f"**Total time**: {total_time:.1f}s | **Avg time per test**: {avg_time:.1f}s\n\n")

        if dim_summary:
            f.write("## Dimension Scores\n\n")
            f.write("| Dimension | Avg | StdDev |\n|---|---|---|\n")
            for dim in ["Framing & Assumptions", "Scope Discipline", "Simplicity", "Verification", "Tradeoffs"]:
                if dim in dim_summary:
                    d = dim_summary[dim]
                    f.write(f"| {dim} | {d['avg']:.2f} | {d['stdev']:.2f} |\n")
            f.write("\n")

        f.write("## Summary\n\n")
        for r in results[:20]:
            status = "OK" if r.passed else "FAIL"
            std_info = f" +/-{r.std_dev:.1f}" if r.repetition_scores and len(r.repetition_scores) > 1 else ""
            raw_snip = (getattr(r, "raw_response", "") or "").replace("\n", " ")[:80]
            raw_part = f" | '{raw_snip}...'" if raw_snip else ""
            f.write(f"- {status} {r.test_id}: {r.score:.1f}{std_info} ({r.time_seconds:.1f}s) - {r.details[:70]}{raw_part}\n")
        f.write("\n**Note**: Full details in the .json file.\n")

    print(f"[REPORT] Saved: {json_path}")
    return json_path


def generate_heatmap(results: List[TestResult], report_dir: Path, suite: str) -> Path:
    """Generate a per-dimension heatmap of judge scores."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = report_dir / f"{timestamp}-heatmap-{suite}.json"

    tests = []
    for r in results:
        js = getattr(r, "judge_scores", None) or {}
        heat_entry = {
            "test_id": r.test_id,
            "category": r.category,
            "overall": r.score,
            "dimensions": js,
            "details": r.details[:100],
        }
        tests.append(heat_entry)

    data = {"suite": suite, "tests": tests, "dimensions": [
        "Framing & Assumptions", "Scope Discipline", "Simplicity", "Verification", "Tradeoffs"
    ]}

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[HEATMAP] Saved: {path}")
    return path


def _serialize_result(r: TestResult) -> Dict:
    d = {
        "test_id": r.test_id, "category": r.category, "score": r.score,
        "passed": r.passed, "details": r.details, "time_seconds": r.time_seconds,
        "prompt_system": r.prompt_system, "prompt_user": r.prompt_user,
        "raw_response": r.raw_response, "self_evaluation": r.self_evaluation,
        "judge_scores": r.judge_scores, "judge_justification": r.judge_justification,
        "n_repetitions": r.n_repetitions, "std_dev": r.std_dev,
        "repetition_scores": r.repetition_scores,
    }
    return {k: v for k, v in d.items() if v is not None}
