# Changelog

All notable changes to llm-behavioral-eval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-27

### Changed
- License switched from MIT to GPL-3.0-only

## [1.0.0] - 2026-06-27

### Added
- Initial release: spec-agnostic LLM behavioral evaluation engine
- 5 test suites: core_principles, rubric_dimensions, roles, variants, concrete
- LLM judge evaluator with per-dimension scoring and justifications
- Concrete code verification with subprocess execution and assertions
- Stratified concrete subtask types with per-type reporting
- N-repetition consistency mode with mean +/- std dev
- A/B Arena mode for head-to-head model comparison with Welch's t-test
- 95% confidence intervals in all reports
- Heatmap generation for per-dimension score analysis
- Judge-vs-exec Pearson correlation analysis
- Spec-agnostic: evaluates any AGENTS.md or eval-profile.json directory
- `behavioral-eval` CLI with full argument support
- 20 unit tests covering scoring, stats, code extraction, and config

[1.0.1]: https://github.com/perezdann/llm-behavioral-eval/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/perezdann/llm-behavioral-eval/releases/tag/v1.0.0
