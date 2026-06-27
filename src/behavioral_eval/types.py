"""Core data types for test cases and results."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TestCase:
    id: str
    category: str
    sub_category: str
    prompt: str
    expected_behaviors: List[str]
    good_response: str
    bad_response: str
    rubric_target: Dict[str, int]
    concrete_assertions: List[Dict] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    test_id: str
    category: str
    score: float
    passed: bool
    details: str
    time_seconds: float = 0.0
    prompt_system: str = ""
    prompt_user: str = ""
    raw_response: str = ""
    self_evaluation: Dict = None
    judge_scores: Dict = None
    judge_justification: str = ""
    n_repetitions: int = 1
    std_dev: float = 0.0
    repetition_scores: Optional[List[float]] = None


RUBRIC_DIMENSIONS = [
    "Framing & Assumptions",
    "Scope Discipline",
    "Simplicity",
    "Verification",
    "Tradeoffs",
]
