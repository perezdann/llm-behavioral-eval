# llm-behavioral-eval

**Spec-agnostic LLM evaluation engine.** Measures how well any LLM follows behavioral specifications (AGENTS.md, CLAUDE.md, .cursorrules, etc.).

## Quick Start

```bash
pip install llm-behavioral-eval

# Evaluate any spec directory
behavioral-eval --spec ./my-project --suite core_principles --count 20 --real-llm

# Full evaluation with LLM judge
behavioral-eval --spec ./dann-specs/project --suite all --real-llm --judge-provider deepseek

# Heuristic mode (no API cost for judge)
behavioral-eval --spec ./dann-specs/project --suite all --real-llm --no-judge

# A/B comparison between two models
behavioral-eval --spec ./dann-specs/project --arena llama-home ollama-home --count 30 --real-llm
```

## Features

- **5 test suites**: core_principles, rubric_dimensions, roles, variants, concrete
- **LLM Judge**: external LLM scores responses per-dimension (1-5) with justifications
- **Concrete verification**: executable coding tasks with real assertion testing
- **Consistency**: `--repetitions N` measures model stability
- **A/B Arena**: compare two models head-to-head with statistical significance
- **Heatmaps**: per-dimension score breakdowns
- **Spec-agnostic**: evaluates any behavioral specification directory
