"""Variants test suite."""

from typing import List

from ..types import TestCase


def generate(variants: List[str], count: int = 25) -> List[TestCase]:
    tests = []
    for i in range(count):
        variant = variants[i % len(variants)]
        prompt = f"Using the {variant} variant: Build a new feature for data processing."

        good = (
            f"Following the {variant} guidelines, I will [domain specific framing]. "
            f"I will prioritize [variant specific emphasis]."
        )
        bad = f"I'll treat this as a generic software task without adapting to the {variant} context."

        tests.append(TestCase(
            id=f"variant-{variant[:25]}-{i:03d}",
            category="variants",
            sub_category=variant,
            prompt=prompt,
            expected_behaviors=[f"Variant specific: {variant}"],
            good_response=good,
            bad_response=bad,
            rubric_target={"Framing & Assumptions": 4},
        ))
    return tests
