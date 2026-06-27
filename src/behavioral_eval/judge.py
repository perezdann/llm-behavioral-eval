"""LLM-as-Judge evaluator: scores responses against a behavioral rubric."""

import json
import re
from typing import Dict, Optional

from .types import TestCase, RUBRIC_DIMENSIONS

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator scoring an AI agent's response against a behavioral specification framework.

Evaluate the response on these 5 dimensions (1-5 each):

1. Framing & Assumptions (1-5): Did the agent explicitly state assumptions and unknowns?
2. Scope Discipline (1-5): Were all changes directly traceable to the request (surgical)?
3. Simplicity (1-5): Was the solution the minimal correct one?
4. Verification (1-5): Did the agent provide concrete evidence that success criteria were met?
5. Tradeoffs (1-5): Did the agent surface important decisions and their implications?

Scoring guide:
- 1: Completely absent or violates the principle
- 2: Mentions it vaguely but no substance
- 3: Adequate, some attempt made
- 4: Good, clear evidence of the principle
- 5: Excellent, exemplary application of the principle

The original task was: {task}

The agent's response:
---
{response}
---

Return ONLY a JSON object (no markdown, no backticks):
{{"Framing & Assumptions": N, "Scope Discipline": N, "Simplicity": N, "Verification": N, "Tradeoffs": N, "overall": N.N, "justification": "Brief explanation of key scores (max 200 chars)"}}

overall is the average of the 5 scores rounded to 1 decimal."""


class JudgeEvaluator:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def evaluate(self, test_case: TestCase, response: str) -> Dict:
        resp = (response or "").strip()
        if not resp or resp.startswith("LLM_ERROR") or resp.startswith("ERROR"):
            return self._fail("empty or error response", {})
        if len(resp) > 10 and resp.count("/") > len(resp) * 0.6:
            return self._fail("garbage output (slashes)", {})

        judge_prompt = JUDGE_SYSTEM_PROMPT.format(
            task=test_case.prompt[:1500], response=resp[:4000]
        )

        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.0,
                max_tokens=600,
            )
            raw_judge = (
                getattr(r.choices[0].message, "content", None)
                or getattr(r.choices[0].message, "reasoning_content", None)
                or ""
            ).strip()

            parsed = self._parse_judge_json(raw_judge)
            if parsed:
                scores = {
                    k: float(v)
                    for k, v in parsed.items()
                    if k in RUBRIC_DIMENSIONS and isinstance(v, (int, float))
                }
                vals = list(scores.values())
                avg = round(sum(vals) / len(vals), 1) if len(vals) >= 4 else float(parsed.get("overall", 2.0))
                return {
                    "score": avg,
                    "passed": avg >= 4.0,
                    "details": f"Judge: avg={avg:.1f}",
                    "judge_scores": scores,
                    "judge_justification": parsed.get("justification", str(raw_judge)[:200]),
                }
            return self._fail(f"parse failed: {raw_judge[:120]}", {})

        except Exception as e:
            return self._fail(f"Judge API error: {str(e)[:100]}", {})

    @staticmethod
    def _fail(reason: str, scores: Dict) -> Dict:
        return {
            "score": 1.0, "passed": False, "details": reason,
            "judge_scores": scores, "judge_justification": reason,
        }

    @staticmethod
    def _parse_judge_json(raw: str) -> Optional[Dict]:
        for candidate in [raw]:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def calibrate(self, good_response: str, bad_response: str) -> Dict:
        """Score known-good and known-bad responses to measure judge bias."""
        good_score = self._evaluate_raw(good_response[:2000])
        bad_score = self._evaluate_raw(bad_response[:2000])
        return {
            "good_score": good_score,
            "bad_score": bad_score,
            "delta": good_score - bad_score,
            "calibrated": (good_score - bad_score) > 1.5,
        }

    def _evaluate_raw(self, text: str) -> float:
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": f"Score this against a behavioral rubric (1-5 overall only, just the number):\n\n{text}"}],
                temperature=0.0,
                max_tokens=10,
            )
            raw = getattr(r.choices[0].message, "content", "3").strip()
            return float(raw[0]) if raw and raw[0].isdigit() else 3.0
        except Exception:
            return 3.0
