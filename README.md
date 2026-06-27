# llm-behavioral-eval

**Spec-agnostic LLM evaluation engine.** Measures how well any LLM follows behavioral
specifications (AGENTS.md, CLAUDE.md, .cursorrules, etc.).

[![PyPI version](https://img.shields.io/pypi/v/llm-behavioral-eval)](https://pypi.org/project/llm-behavioral-eval/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Unlike traditional benchmarks (HumanEval, MT-Bench, SWE-bench) that measure *what* an LLM
produces, llm-behavioral-eval measures *how* it thinks — does it state assumptions, stay
in scope, verify its work, and surface tradeoffs?

## Quick Start

```bash
pip install llm-behavioral-eval

# Evaluate any project with an AGENTS.md
behavioral-eval --spec ./my-project --suite core_principles --count 20 --real-llm

# Full evaluation with LLM judge (recommended)
behavioral-eval --spec ./my-project --suite all --real-llm \
  --provider ollama --judge-provider deepseek

# Heuristic mode (fast, no API cost for judge)
behavioral-eval --spec ./my-project --suite all --real-llm --no-judge
```

## Test Suites

| Suite | What it tests | Scoring | Recommended n |
|---|---|---|---|
| `core_principles` | 7 behavioral principles (framing, simplicity, surgical, verification, tradeoffs...) | Judge or heuristic | 20 |
| `rubric_dimensions` | 5 evaluation dimensions with per-dimension focus | Judge or heuristic | 40 |
| `roles` | 13 specialist role adherence (physician, lawyer, architect...) | Judge or heuristic | 40 |
| `variants` | 7 domain-specific variant adherence (devops, research, education...) | Judge or heuristic | 25 |
| `concrete` | Executable coding tasks with real assertion testing | Code execution | 30 (stratified) |

## Features

### LLM Judge Evaluator
An external LLM scores each response on 5 dimensions (1-5) with justifications:
- **Framing & Assumptions**: Did the agent state assumptions and unknowns?
- **Scope Discipline**: Were changes traceable to the request (surgical)?
- **Simplicity**: Was the solution minimal and correct?
- **Verification**: Was concrete evidence provided?
- **Tradeoffs**: Were decisions and implications surfaced?

```bash
behavioral-eval --spec ./my-project --suite all --real-llm --judge-provider deepseek
```

### Concrete Verification
The `concrete` suite generates coding tasks with actual assertion testing.
The engine extracts code from the response, executes it in a subprocess,
and verifies it against test cases.

5 subtask types (stratified): email_validator, fibonacci, word_counter, surgical_fix, temperature_converter.

### Consistency Metrics
Run each test multiple times to measure model stability:

```bash
behavioral-eval --spec ./my-project --suite core_principles --real-llm --repetitions 3
```

Reports include mean, standard deviation, and 95% confidence intervals.

### A/B Arena
Head-to-head comparison between two models:

```bash
behavioral-eval --spec ./my-project --arena ollama-home llama-home --count 30 --real-llm
```

Uses Welch's t-test to determine if score differences are statistically significant.

### Heatmaps
Per-dimension score breakdowns for visual analysis:

```bash
behavioral-eval --spec ./my-project --suite all --real-llm --judge-provider deepseek --heatmap
```

### Statistical Reporting
Every report includes:
- 95% confidence intervals around the mean score
- Dimension-level aggregate scores (when using judge)
- Pearson correlation between judge scores and execution scores (for concrete suite)
- Stratified subtask breakdown (for concrete suite)

## Provider Configuration

Providers are configured in a JSON file (default location: `local/llm-providers.json`
relative to spec path):

```json
{
  "default_provider": "ollama",
  "judge_provider": "deepseek",
  "providers": {
    "ollama": {
      "type": "openai-compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model": "llama3.1:70b"
    },
    "deepseek": {
      "type": "openai-compatible",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-your-deepseek-key",
      "model": "deepseek-chat"
    }
  }
}
```

Override with `--config path/to/providers.json` or `--provider name`.

## Spec Profile

Any directory containing an AGENTS.md can be evaluated. For advanced configuration,
add an `eval-profile.json`:

```json
{
  "name": "my-spec",
  "spec_files": {
    "core": "AGENTS.md",
    "compact": "mini/core.md",
    "rubric": "evaluation-rubric.md"
  },
  "roles_dir": "roles",
  "variants_dir": "variants",
  "suites": {
    "core_principles": { "count": 20 },
    "concrete": { "count": 30, "stratified": true }
  },
  "principles": ["Think & Frame", "Simplicity First", "..."],
  "rubric_dimensions": ["Framing & Assumptions", "..."],
  "roles": ["engineer", "designer", "..."],
  "variants": ["web", "mobile", "..."]
}
```

## Version Control

This project uses:
- **Conventional commits** (`feat:`, `fix:`, `docs:`) via [commitizen](https://commitizen-tools.github.io/commitizen/)
- **Semantic versioning**: `cz bump` auto-bumps version and updates CHANGELOG.md
- **Pre-commit hooks**: ruff linting + pytest on every commit
- **GitHub Actions**: CI (test+lint on push), PyPI publish (on tag `v*`)

## License

GPL-3.0-only. See [LICENSE](LICENSE).
