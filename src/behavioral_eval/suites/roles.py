"""Roles test suite."""

from typing import List

from ..types import TestCase


def generate(roles: List[str], count: int = 40) -> List[TestCase]:
    tests = []
    for i in range(count):
        role = roles[i % len(roles)]
        task = f"Help with a task in the domain of {role.replace('-', ' ')}."
        prompt = f"You are in the role of {role}. {task} Apply behavioral specification principles."

        good = (
            f"As a {role}, I will frame the problem according to domain best practices. "
            f"I will make surgical, minimal changes. I will define clear success criteria "
            f"and verify them with domain-appropriate checks."
        )
        bad = f"I'll just do the task in a general way without considering the specific domain needs of a {role}."

        tests.append(TestCase(
            id=f"role-{role[:20]}-{i:03d}",
            category="roles",
            sub_category=role,
            prompt=prompt,
            expected_behaviors=[f"Role adherence: {role}"],
            good_response=good,
            bad_response=bad,
            rubric_target={"Scope Discipline": 4, "Verification": 4},
        ))
    return tests
