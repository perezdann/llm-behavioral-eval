"""Tests for behavioral_eval — no LLM calls needed."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from behavioral_eval.scoring import (
    score_heuristic,
    verify_code_execution,
    _extract_code,
)
from behavioral_eval.stats import (
    confidence_interval,
    mean_std,
    required_sample_size,
    compute_correlation,
)
from behavioral_eval.config import load_spec_profile


class TestHeuristicScoring:
    def test_empty_response(self):
        result = score_heuristic(None, "")
        assert result["score"] == 1.0
        assert not result["passed"]

    def test_slash_garbage(self):
        result = score_heuristic(None, "///" * 100)
        assert result["score"] == 1.0
        assert "garbage" in result["details"]

    def test_good_framing_and_verification(self):
        response = "Assumptions: The system uses OAuth. Verification: I ran the test suite and all 15 tests passed. Only minimal changes to auth.py."
        result = score_heuristic(None, response)
        assert result["score"] >= 3.5, f"Expected >= 3.5, got {result['score']}"
        assert "framing" in result["details"].lower()

    def test_scope_creep_penalty(self):
        response = "I'll fix the bug. Also while I'm at it, I'll refactor the entire module and add an extra feature."
        result = score_heuristic(None, response)
        assert result["score"] <= 2.5, f"Expected <= 2.5, got {result['score']}"

    def test_short_no_signals(self):
        response = "ok done"
        result = score_heuristic(None, response)
        assert result["score"] <= 1.5


class TestCodeExtraction:
    def test_extract_fenced_code(self):
        response = "Here is the code:\n```python\ndef foo():\n    return 42\n```\n"
        code = _extract_code(response)
        assert "def foo()" in code
        assert "return 42" in code

    def test_extract_no_fence(self):
        response = "def bar():\n    return 1\n"
        code = _extract_code(response)
        assert "def bar()" in code

    def test_extract_no_code(self):
        response = "Here's how I would do it..."
        code = _extract_code(response)
        assert code == ""


class TestCodeVerification:
    def test_passing_code(self):
        code = "def is_valid_email(email: str) -> bool:\n    return '@' in email and '.' in email.split('@')[-1]"
        response = f"```python\n{code}\n```"
        assertions = [
            {"input": "test@example.com", "expected": True},
            {"input": "invalid", "expected": False},
        ]
        result = verify_code_execution(response, assertions, [])
        assert result["score"] >= 3.0
        assert "2/2" in result["details"]

    def test_forbidden_pattern(self):
        code = "def is_valid_email(email: str) -> bool:\n    return '@' in email\n\nimport os"
        response = f"```python\n{code}\n```"
        result = verify_code_execution(response, [], ["import "])
        assert "forbidden" in result["details"]

    def test_no_code_in_response(self):
        result = verify_code_execution(
            "just text, no code", [{"input": 1, "expected": 1}], []
        )
        assert result["score"] == 1.0


class TestStatistics:
    def test_mean_std(self):
        mu, std = mean_std([2.0, 3.0, 4.0])
        assert mu == 3.0
        assert std == pytest.approx(1.0)

    def test_mean_std_single(self):
        mu, std = mean_std([5.0])
        assert mu == 5.0
        assert std == 0.0

    def test_confidence_interval(self):
        mu, lo, hi = confidence_interval([2.0, 3.0, 4.0])
        assert mu == 3.0
        assert lo < 3.0 < hi

    def test_required_sample_size(self):
        n = required_sample_size(1.0, target_margin=0.3)
        assert n >= 40  # roughly

    def test_correlation_perfect(self):
        r = compute_correlation([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert r["r"] == pytest.approx(1.0, abs=0.01)

    def test_correlation_negative(self):
        r = compute_correlation([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        assert r["r"] == pytest.approx(-1.0, abs=0.01)

    def test_correlation_too_few(self):
        r = compute_correlation([1, 2], [1, 2])
        assert r["r"] is None


class TestSpecProfile:
    def test_auto_detect_spec(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "AGENTS.md").write_text("# Test spec")
            (root / "mini").mkdir()
            (root / "mini" / "core.md").write_text("# Core")
            profile = load_spec_profile(root)
            assert profile["name"] == Path(d).name
            assert profile["spec_files"]["core"] == "AGENTS.md"
            assert profile["spec_files"]["compact"] == "mini/core.md"
            assert profile["principles"][0] == "Think & Frame Before Acting"

    def test_eval_profile_json(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "eval-profile.json").write_text(
                json.dumps(
                    {"name": "custom", "suites": {"core_principles": {"count": 5}}}
                )
            )
            profile = load_spec_profile(root)
            assert profile["name"] == "custom"
            assert profile["suites"]["core_principles"]["count"] == 5
