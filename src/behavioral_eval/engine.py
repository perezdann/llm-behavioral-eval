"""Core evaluation engine: spec-agnostic, runs suites against any LLM."""

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from .config import get_provider, load_provider_config, load_spec_profile
from .judge import JudgeEvaluator
from .reports import generate_heatmap, generate_report
from .scoring import score_heuristic, verify_code_execution
from .stats import compute_correlation, mean_std
from .types import TestCase, TestResult

SUITE_GENERATORS = {}


def _init_generators():
    if SUITE_GENERATORS:
        return
    from .suites import concrete, core_principles, roles, rubric, variants

    SUITE_GENERATORS.update({
        "core_principles": core_principles.generate,
        "rubric_dimensions": rubric.generate,
        "roles": roles.generate,
        "variants": variants.generate,
        "concrete": concrete.generate,
    })


class EvaluationEngine:
    def __init__(
        self,
        spec_path: Path,
        provider: Optional[str] = None,
        config_path: Optional[Path] = None,
        judge_provider: Optional[str] = None,
        judge_model: Optional[str] = None,
        repetitions: int = 1,
        use_real_llm: bool = False,
    ):
        _init_generators()
        self.spec_path = spec_path.resolve()
        self.spec_profile = load_spec_profile(self.spec_path)
        self.use_real_llm = use_real_llm
        self.repetitions = max(1, repetitions)
        self.results: List[TestResult] = []
        self.llm_client = None
        self.model = "unknown"
        self.judge_evaluator = None
        self.judge_provider_name = judge_provider
        self.judge_model = None

        self.provider_cfg = load_provider_config(config_path, spec_path=self.spec_path.parent)
        self.provider_name = "simulated"
        self.provider = {}
        self.model = "simulated"

        if use_real_llm:
            prov = get_provider(self.provider_cfg, provider)
            self.provider = prov
            self.provider_name = provider or self.provider_cfg.get("default_provider", "env")
            base = prov.get("base_url", "http://localhost:8080/v1")
            key = prov.get("api_key", "")
            model_cfg = prov.get("model", "local")

            self.llm_client = OpenAI(base_url=base, api_key=key)
            self.model = model_cfg

            try:
                models = self.llm_client.models.list()
                ids = [m.id for m in getattr(models, "data", [])]
                if ids and model_cfg.lower() in ("llama", "local", "default", ""):
                    self.model = ids[0]
                    print(f"[INFO] Auto-selected model: {self.model}")
                print(f"[INFO] Available models: {ids[:3]}")
            except Exception:
                pass
            print(f"[INFO] Provider '{self.provider_name}' -> {base} (model={self.model})")

        if judge_provider:
            jprov = get_provider(self.provider_cfg, judge_provider)
            jbase = jprov.get("base_url", "")
            jkey = jprov.get("api_key", "")
            jmodel = judge_model or jprov.get("model", "gpt-4o-mini")
            if jkey and jkey not in ("DEEPSEEK_API_KEY_PLACEHOLDER", "sk-YOUR_DEEPSEEK_API_KEY"):
                self.judge_client = OpenAI(base_url=jbase, api_key=jkey)
                self.judge_evaluator = JudgeEvaluator(self.judge_client, jmodel)
                self.judge_model = jmodel
                print(f"[INFO] Judge: '{judge_provider}' -> {jbase} (model={jmodel})")
            else:
                print(f"[WARN] Judge provider '{judge_provider}' has no valid API key. Using heuristic scoring.")

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        if not self.llm_client:
            return "ERROR: LLM client not initialized"

        def _chat(msgs, mt, temp):
            r = self.llm_client.chat.completions.create(
                model=self.model, messages=msgs, temperature=temp, max_tokens=mt
            )
            msg = r.choices[0].message
            content = (getattr(msg, "content", None) or "").strip()
            reasoning = (getattr(msg, "reasoning_content", None) or "").strip()
            if not content and reasoning:
                content = reasoning
            if not content:
                extra = getattr(msg, "model_extra", None) or {}
                content = (extra.get("reasoning_content") or "").strip() or content
            return content or ""

        full_prompt = (system_prompt or "") + "\n\n" + (user_prompt or "")

        for params in [(max_tokens, 0.2), (400, 0.5), (500, 0.3)]:
            try:
                msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
                content = _chat(msgs, params[0], params[1])
                if content:
                    return content
            except Exception:
                pass

        try:
            r = self.llm_client.completions.create(
                model=self.model, prompt=full_prompt[:1800], temperature=0.3, max_tokens=500
            )
            txt = getattr(r.choices[0], "text", "") if r.choices else ""
            return (txt or "").strip()
        except Exception as e:
            return f"LLM_ERROR: {str(e)}"

    def _build_system_prompt(self, test: TestCase) -> str:
        spec_root = Path(self.spec_profile["_spec_root"])
        spec_files = self.spec_profile.get("spec_files", {})

        core = ""
        compact = spec_files.get("compact", "mini/core.md")
        core_path = spec_root / compact
        if core_path.exists():
            core = core_path.read_text().strip() + "\n\n"
        else:
            core_path = spec_root / spec_files.get("core", "AGENTS.md")
            if core_path.exists():
                core = core_path.read_text()[:2000] + "\n\n---\n\n"

        specific = ""
        if test.category == "roles":
            role_path = spec_root / self.spec_profile.get("roles_dir", "roles") / f"{test.sub_category}.md"
            if role_path.exists():
                specific = f"\n\nRole: {test.sub_category}\n{role_path.read_text()[:800]}\n"
        elif test.category == "variants":
            var_path = spec_root / self.spec_profile.get("variants_dir", "variants") / test.sub_category / "AGENTS.md"
            if var_path.exists():
                specific = f"\n\nVariant: {test.sub_category}\n{var_path.read_text()[:700]}\n"

        return core + specific + "\nApply the principles above. Respond structured and be explicit."

    def score(self, test: TestCase, response: str) -> Dict:
        resp = (response or "").strip()
        if not resp or resp.startswith("LLM_ERROR") or resp.startswith("ERROR"):
            return {"score": 1.0, "passed": False, "details": "empty or error", "judge_scores": {}, "judge_justification": ""}
        if len(resp) > 10 and resp.count("/") > len(resp) * 0.6:
            return {"score": 1.0, "passed": False, "details": "garbage (slashes)", "judge_scores": {}, "judge_justification": ""}

        if test.concrete_assertions:
            return verify_code_execution(resp, test.concrete_assertions, test.forbidden_patterns)

        if self.judge_evaluator:
            return self.judge_evaluator.evaluate(test, resp)

        return score_heuristic(test, resp)

    def run_suite(self, suite_name: str, count_override: Optional[int] = None) -> List[TestResult]:
        generators = SUITE_GENERATORS
        profile_suites = self.spec_profile.get("suites", {})

        if suite_name == "all":
            all_results = []
            for s in generators:
                all_results.extend(self.run_suite(s, count_override))
            return all_results

        if suite_name not in generators:
            raise ValueError(f"Unknown suite: {suite_name}. Available: {list(generators)}")

        suite_cfg = profile_suites.get(suite_name, {})
        count = count_override or suite_cfg.get("count", 30)
        stratified = suite_cfg.get("stratified", False)
        kwargs = {}
        if suite_name == "core_principles":
            kwargs["principles"] = self.spec_profile.get("principles", [])
        elif suite_name == "rubric_dimensions":
            kwargs["dimensions"] = self.spec_profile.get("rubric_dimensions", [])
        elif suite_name == "roles":
            kwargs["roles"] = self.spec_profile.get("roles", [])
        elif suite_name == "variants":
            kwargs["variants"] = self.spec_profile.get("variants", [])
        elif suite_name == "concrete":
            kwargs["stratified"] = stratified

        gen_func = generators[suite_name]
        gen_varnames = gen_func.__code__.co_varnames[:gen_func.__code__.co_argcount]
        all_kwargs = {"count": count, **kwargs}
        filtered_kwargs = {k: v for k, v in all_kwargs.items() if k in gen_varnames}
        test_cases = gen_func(**filtered_kwargs)
        results = []

        judge_label = f", judge={self.judge_provider_name}" if self.judge_evaluator else ""
        print(f"\n=== {suite_name} ({len(test_cases)} tests{judge_label}) ===")
        start_time = time.time()

        for idx, tc in enumerate(test_cases, 1):
            rep_scores, rep_times, rep_results = [], [], []

            for rep in range(self.repetitions if self.use_real_llm else 1):
                rep_label = f" [rep {rep+1}/{self.repetitions}]" if self.repetitions > 1 else ""
                print(f"  [{idx}/{len(test_cases)}] {tc.id}{rep_label} ... ", end="", flush=True)
                t0 = time.time()

                if self.use_real_llm:
                    result = self._run_real_test(tc)
                else:
                    eval_result = self.score(tc, tc.good_response)
                    result = TestResult(
                        test_id=tc.id, category=tc.category, score=eval_result["score"],
                        passed=eval_result["passed"], details=f"Sim: {eval_result['details']}",
                        time_seconds=0, raw_response=tc.good_response,
                    )

                rep_scores.append(result.score)
                rep_times.append(result.time_seconds)
                rep_results.append(result)

                preview = (result.raw_response or "").replace("\n", " ")[:80] if self.use_real_llm else ""
                extra = f" | '{preview}...'" if preview else ""
                print(f"{result.score:.1f} ({result.time_seconds:.1f}s){extra}")

            if self.repetitions > 1 and self.use_real_llm:
                avg_score, std_dev = mean_std(rep_scores)
                base = rep_results[0]
                base.score = round(avg_score, 1)
                base.passed = avg_score >= 4.0
                base.std_dev = round(std_dev, 2)
                base.n_repetitions = self.repetitions
                base.repetition_scores = rep_scores
                base.time_seconds = sum(rep_times)
                results.append(base)
            else:
                results.append(rep_results[0])

            self._save_partial(results, suite_name)

        print(f"--- {suite_name} completed in {time.time() - start_time:.1f}s ---")
        return results

    def _run_real_test(self, tc: TestCase) -> TestResult:
        t0 = time.time()
        system = self._build_system_prompt(tc)
        user = tc.prompt.split("\n\nFollow")[0] if "\n\nFollow" in tc.prompt else tc.prompt

        if tc.category != "concrete":
            user += """

Respond with explicit structure (after any thinking/reasoning):
Assumptions: ...
Plan: ...
[minimal answer here]
Verification: ...
```json
{"Framing & Assumptions": N, "Scope Discipline": N, "Simplicity": N, "Verification": N, "Tradeoffs": N, "comment": "..."}
```
Follow the principles strictly. Keep concise but complete."""

        actual = self._call_llm(system, user)
        raw = actual or ""

        if raw.startswith("LLM_ERROR") or raw.startswith("ERROR") or len(raw.strip()) < 3:
            return TestResult(
                test_id=tc.id, category=tc.category, score=1.0, passed=False,
                details=f"FAILED: {raw[:120]}", time_seconds=time.time() - t0,
                prompt_system=system, prompt_user=user, raw_response=raw,
            )

        eval_result = self.score(tc, raw)
        self_eval = {}
        if tc.category != "concrete":
            try:
                fenced = re.search(r"```json\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
                candidate = fenced.group(1) if fenced else raw
                m = re.search(r"\{[\s\S]*\}", candidate)
                if m:
                    parsed = json.loads(m.group(0))
                    self_eval = {k: float(v) for k, v in parsed.items() if isinstance(v, (int, float))}
                    if self_eval and not self.judge_evaluator:
                        vals = list(self_eval.values())
                        eval_result["score"] = round(sum(vals) / len(vals), 1)
                        eval_result["passed"] = eval_result["score"] >= 4.0
            except Exception:
                pass

        return TestResult(
            test_id=tc.id, category=tc.category, score=eval_result["score"],
            passed=eval_result["passed"], details=f"Real: {eval_result['details']}",
            time_seconds=time.time() - t0, prompt_system=system, prompt_user=user,
            raw_response=raw, self_evaluation=self_eval,
            judge_scores=eval_result.get("judge_scores", {}),
            judge_justification=eval_result.get("judge_justification", ""),
        )

    def _save_partial(self, results: List[TestResult], suite: str):
        results_dir = self.spec_path / "tests" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        out_path = results_dir / f"{suite}_results.json"
        with open(out_path, "w") as f:
            json.dump([_serialize(r) for r in results], f, indent=2)

    def save_results(self, results: List[TestResult], suite: str):
        results_dir = self.spec_path / "tests" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        out_path = results_dir / f"{suite}_results.json"
        with open(out_path, "w") as f:
            json.dump([_serialize(r) for r in results], f, indent=2)

        passed = sum(1 for r in results if r.passed)
        avg = sum(r.score for r in results) / len(results) if results else 0
        print(f"\n=== {suite.upper()} ===")
        print(f"Tests: {len(results)} | Passed: {passed} ({passed/len(results)*100:.0f}%) | Avg: {avg:.2f}")

        report_dir = self.spec_path / "reports"
        generate_report(
            results, suite, self.provider_name, self.model, report_dir,
            self.judge_provider_name, self.judge_model, self.repetitions,
        )

    def print_summary(self, results: List[TestResult]):
        by_suite = defaultdict(list)
        for r in results:
            by_suite[r.category].append(r)

        # Stratified concrete breakdown
        concrete_by_type = defaultdict(list)
        for r in by_suite.get("concrete", []):
            js = getattr(r, "judge_scores", None) or {}
            sub = js.get("sub_category", getattr(r, "test_id", "").split("-")[1] if "-" in r.test_id else "?")
            concrete_by_type[getattr(r, "test_id", "").rsplit("-", 1)[0].replace("concrete-", "")].append(r.score)

        suite_order = ["core_principles", "rubric_dimensions", "roles", "variants", "concrete"]
        total_all = total_passed = total_scores = 0

        print("\n" + "=" * 65)
        print("OVERALL SUMMARY")
        print("=" * 65)
        for s in suite_order:
            res = by_suite.get(s, [])
            n = len(res)
            if not n:
                continue
            scores = [r.score for r in res]
            avg = sum(scores) / n
            pct = sum(1 for r in res if r.passed) / n * 100
            total_all += n
            total_passed += sum(1 for r in res if r.passed)
            total_scores += sum(scores)

            from .stats import confidence_interval
            _, ci_low, ci_high = confidence_interval(scores) if n >= 2 else (avg, avg, avg)
            print(f"  {s:25s} {n:3d} tests  passed: {sum(1 for r in res if r.passed):3d}/{n} ({pct:.0f}%)  avg: {avg:.2f} [95% CI: {ci_low:.2f}-{ci_high:.2f}]")

        if total_all:
            overall_avg = total_scores / total_all
            print(f"  {'TOTAL':25s} {total_all:3d} tests  passed: {total_passed:3d}/{total_all} ({total_passed/total_all*100:.0f}%)  avg: {overall_avg:.2f}")

        # Stratified concrete breakdown
        if concrete_by_type:
            print(f"\n  Concrete breakdown by subtask type:")
            for tname, vals in sorted(concrete_by_type.items()):
                if vals:
                    print(f"    {tname:30s} n={len(vals):2d}  avg={sum(vals)/len(vals):.2f}")

        # Correlation analysis
        judge_scores_all = []
        exec_scores_all = []
        for r in by_suite.get("concrete", []):
            js = getattr(r, "judge_scores", None) or {}
            if js:
                judge_scores_all.append(sum(js.values()) / len(js) if js else 0)
                exec_scores_all.append(r.score)
        if len(judge_scores_all) >= 5:
            corr = compute_correlation(judge_scores_all, exec_scores_all)
            print(f"\n  Judge-vs-Exec correlation: r={corr.get('r', 'N/A')} ({corr.get('interpretation', '?')})  n={corr.get('n', 0)}")

    def generate_heatmap(self, results: List[TestResult], suite: str):
        report_dir = self.spec_path / "reports"
        generate_heatmap(results, report_dir, suite)


def _serialize(r: TestResult) -> Dict:
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
