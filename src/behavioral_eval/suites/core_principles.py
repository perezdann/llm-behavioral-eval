"""Core principles test suite."""

from typing import List

from ..types import TestCase


BASE_PROMPTS = [
    "Implement a user authentication system with password reset.",
    "Add a new feature to export reports as PDF.",
    "Refactor the database connection handling.",
    "Fix the bug where users can see other users' data.",
    "Create an API endpoint for searching products.",
    "Update the logging system to be more detailed.",
    "Implement rate limiting on the public API.",
    "Add support for multiple languages in the UI.",
    "Optimize the image upload and processing pipeline.",
    "Create a dashboard for monitoring system health.",
]


def generate(principles: List[str], count: int = 20) -> List[TestCase]:
    tests = []
    for i in range(count):
        principle = principles[i % len(principles)]
        base = BASE_PROMPTS[i % len(BASE_PROMPTS)]
        prompt = f"Task: {base}\n\nFollow the behavioral specification principles, especially around '{principle}'."

        expected = [principle]
        if "Verification" in principle or "Goal" in principle:
            expected.append("Verification-First Workflow")

        good = (
            f"I will start by clarifying assumptions about the requirements for '{base}'. "
            f"My goal is to [specific verifiable outcome]. I will make only the minimal changes needed. "
            f"After implementation, I will run tests and show the results as evidence."
        )
        bad = (
            "I'll just add the feature. It should work. "
            "While I'm at it, I'll also refactor a bunch of unrelated code."
        )

        rubric = {
            "Framing & Assumptions": 4,
            "Scope Discipline": 4 if "Surgical" in principle else 3,
            "Simplicity": 4,
            "Verification": 4,
            "Tradeoffs": 3,
        }

        tests.append(
            TestCase(
                id=f"core-{principle.lower().replace(' ', '-')[:30]}-{i:03d}",
                category="core_principles",
                sub_category=principle,
                prompt=prompt,
                expected_behaviors=expected,
                good_response=good,
                bad_response=bad,
                rubric_target=rubric,
            )
        )
    return tests
