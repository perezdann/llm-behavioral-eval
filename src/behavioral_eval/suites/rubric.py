"""Rubric dimensions test suite."""

from typing import List

from ..types import TestCase


SCENARIOS = [
    "Add a simple validation to a form field.",
    "Migrate a legacy module to a new framework.",
    "Debug why a scheduled job is failing intermittently.",
    "Design a new caching layer for the application.",
    "Write documentation for an existing complex feature.",
]


def generate(dimensions: List[str], count: int = 40) -> List[TestCase]:
    tests = []
    for i in range(count):
        dim = dimensions[i % len(dimensions)]
        scenario = SCENARIOS[i % len(SCENARIOS)]
        prompt = f"Task: {scenario}\nFocus especially on the '{dim}' dimension."

        good = (
            f"Before starting, I stated my assumptions clearly. I will only change files directly "
            f"related to the task. The solution is minimal. After changes, I ran the relevant tests "
            f"and here are the passing results: [evidence]. Tradeoff considered: X vs Y."
        )
        bad = "I made several changes across the codebase to improve things."

        rubric = {d: 4 for d in dimensions}
        rubric[dim] = 5

        tests.append(TestCase(
            id=f"rubric-{dim.lower().replace(' ', '-')[:25]}-{i:03d}",
            category="rubric_dimensions",
            sub_category=dim,
            prompt=prompt,
            expected_behaviors=[dim],
            good_response=good,
            bad_response=bad,
            rubric_target=rubric,
        ))
    return tests
