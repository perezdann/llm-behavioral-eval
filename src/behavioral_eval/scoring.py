"""Scoring strategies: judge-based, heuristic keyword, and concrete code execution."""

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List

from .types import TestCase


def score_heuristic(test: TestCase, response: str) -> Dict:
    """Keyword-based heuristic scoring (fast, no API cost)."""
    resp = (response or "").strip()
    if not resp or resp.startswith("LLM_ERROR") or resp.startswith("ERROR"):
        return {"score": 1.0, "passed": False, "details": "empty or error", "judge_scores": {}, "judge_justification": ""}
    if len(resp) > 10 and resp.count("/") > len(resp) * 0.6:
        return {"score": 1.0, "passed": False, "details": "garbage (slashes)", "judge_scores": {}, "judge_justification": ""}

    score = 1.8
    details = []
    resp_lower = resp.lower()
    words = resp.split()
    resp_len = len(words)

    framing_kw = ["assumption", "assume", "i assume", "unknown", "clarif", "assumptions:"]
    if any(kw in resp_lower for kw in framing_kw):
        score += 0.8; details.append("framing")

    verify_kw = ["test", "verify", "evidence", "passed", "output:", "metric", "verification:"]
    if any(kw in resp_lower for kw in verify_kw):
        score += 1.0; details.append("verification")

    surgical_kw = ["only", "minimal", "surgical", "just the", "no other changes", "scoped", "minimal change"]
    if any(kw in resp_lower for kw in surgical_kw):
        score += 0.7; details.append("surgical/minimal")

    if resp_len < 180 and details:
        score += 0.5; details.append("concise+structured")

    creep_kw = ["while i'm at it", "also refactor", "extra feature", "bonus", "unrelated"]
    if any(kw in resp_lower for kw in creep_kw):
        score -= 1.0; details.append("scope creep")

    if not details and resp_len > 20:
        score = min(score, 2.4)
    if resp_len < 15 and not details:
        score = 1.2

    score = max(1.0, min(5.0, round(score, 1)))
    return {
        "score": score, "passed": score >= 4.0,
        "details": "; ".join(details) if details else "no explicit principles shown",
        "judge_scores": {}, "judge_justification": "",
    }


def verify_code_execution(response: str, assertions: List[Dict], forbidden: List[str]) -> Dict:
    """Extract Python code from response, run tests, check forbidden patterns."""
    code = _extract_code(response)
    if not code or "def " not in code:
        return {"score": 1.0, "passed": False, "details": "no executable function found"}

    for pattern in forbidden:
        try:
            if re.search(pattern, code):
                return {"score": 2.0, "passed": False, "details": f"forbidden pattern: {pattern}"}
        except re.error:
            pass

    passed = 0
    total = len(assertions)
    for assertion in assertions:
        try:
            import_fn = assertion["input"]
            expected = assertion["expected"]
            func_name = code.split("def ")[1].split("(")[0]
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(code + f"\n\nimport json\n_result = {func_name}({json.dumps(import_fn)})\nprint(json.dumps(_result))\n")
                    tmp_path = f.name
                result = subprocess.run(
                    [sys.executable, tmp_path], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    actual = json.loads(result.stdout.strip())
                    if actual == expected:
                        passed += 1
            finally:
                if tmp_path:
                    try: os.unlink(tmp_path)
                    except OSError: pass
        except Exception:
            pass

    pass_rate = passed / total if total > 0 else 0
    score = 1.0 + (pass_rate * 4.0)
    return {
        "score": round(score, 1),
        "passed": score >= 4.0,
        "details": f"exec: {passed}/{total} assertions passed",
    }


def _extract_code(response: str) -> str:
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", response)
    if m:
        return m.group(1).strip()
    lines = response.strip().split("\n")
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith("def ") or in_code:
            in_code = True
            code_lines.append(line)
    return "\n".join(code_lines) if code_lines else ""
