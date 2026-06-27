"""Statistical helpers: confidence intervals, correlation, repetition aggregation."""

import math
import statistics
from typing import Dict, List, Tuple


def mean_std(scores: List[float]) -> Tuple[float, float]:
    if len(scores) <= 1:
        return scores[0] if scores else 0.0, 0.0
    return statistics.mean(scores), statistics.stdev(scores)


def confidence_interval(scores: List[float], z: float = 1.96) -> Tuple[float, float, float]:
    """Returns (mean, lower_bound, upper_bound) for 95% CI (z=1.96)."""
    if len(scores) < 2:
        return scores[0] if scores else 0, scores[0] if scores else 0, scores[0] if scores else 0
    mu = statistics.mean(scores)
    se = statistics.stdev(scores) / math.sqrt(len(scores))
    margin = z * se
    return mu, max(1.0, mu - margin), min(5.0, mu + margin)


def required_sample_size(stdev: float, target_margin: float = 0.3, z: float = 1.96) -> int:
    """Tests needed to achieve given margin of error."""
    if stdev <= 0:
        return 1
    return math.ceil((z * stdev / target_margin) ** 2)


def detect_difference(scores_a: List[float], scores_b: List[float], delta: float = 0.5) -> Dict:
    """Welch's t-test to check if two score sets differ significantly."""
    try:
        from scipy import stats as scipy_stats
    except ImportError:
        return {"significant": False, "reason": "scipy not installed"}

    if len(scores_a) < 3 or len(scores_b) < 3:
        return {"significant": False, "reason": "need >= 3 samples per group"}

    t_stat, p_value = scipy_stats.ttest_ind(scores_a, scores_b, equal_var=False)
    mu_a, mu_b = statistics.mean(scores_a), statistics.mean(scores_b)
    return {
        "significant": p_value < 0.05 and abs(mu_a - mu_b) >= delta,
        "p_value": round(p_value, 4),
        "mean_a": round(mu_a, 2),
        "mean_b": round(mu_b, 2),
        "delta": round(mu_a - mu_b, 2),
    }


def compute_correlation(judge_scores: List[float], exec_scores: List[float]) -> Dict:
    """Pearson correlation between judge scores and execution scores."""
    if len(judge_scores) < 5 or len(exec_scores) < 5:
        return {"r": None, "reason": "need >= 5 pairs"}
    n = min(len(judge_scores), len(exec_scores))
    try:
        from scipy import stats as scipy_stats
        r, p = scipy_stats.pearsonr(judge_scores[:n], exec_scores[:n])
        return {"r": round(r, 3), "p_value": round(p, 4), "n": n,
                "interpretation": "strong" if abs(r) > 0.5 else ("moderate" if abs(r) > 0.3 else "weak")}
    except ImportError:
        # Fallback: manual Pearson
        x, y = judge_scores[:n], exec_scores[:n]
        mx, my = statistics.mean(x), statistics.mean(y)
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
        if dx == 0 or dy == 0:
            return {"r": 0.0, "p_value": 1.0, "n": n}
        r = num / (dx * dy)
        return {"r": round(r, 3), "p_value": None, "n": n,
                "interpretation": "strong" if abs(r) > 0.5 else ("moderate" if abs(r) > 0.3 else "weak")}
