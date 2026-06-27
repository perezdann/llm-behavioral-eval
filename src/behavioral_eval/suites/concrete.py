"""Concrete test suite with stratified subtask types and executable verification."""

from typing import Dict, List

from ..types import TestCase

# Each subtask has its own difficulty profile. Scores are reported per-type + overall.
SUBTASKS: Dict[str, Dict] = {
    "email_validator": {
        "principle": "Simplicity & Minimum Viable",
        "prompt": (
            "Write a Python function `is_valid_email(email: str) -> bool` that validates email addresses. "
            "Return ONLY the function code (no explanations, no extra functions). "
            "The function should check for: presence of @, non-empty local part, non-empty domain with a dot."
        ),
        "assertions": [
            {"input": "test@example.com", "expected": True},
            {"input": "invalid", "expected": False},
            {"input": "user@domain", "expected": False},
            {"input": "@domain.com", "expected": False},
            {"input": "user@.com", "expected": False},
        ],
        "forbidden": ["def (?!is_valid_email\\b)\\w+", "class ", "import "],
    },
    "fibonacci": {
        "principle": "Goal-Driven with Verification",
        "prompt": (
            "Write a Python function `fibonacci(n: int) -> list` that returns the first n Fibonacci numbers. "
            "Return ONLY the function code. Use iteration, not recursion."
        ),
        "assertions": [
            {"input": 5, "expected": [0, 1, 1, 2, 3]},
            {"input": 1, "expected": [0]},
            {"input": 0, "expected": []},
            {"input": 10, "expected": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]},
        ],
        "forbidden": ["def (?!fibonacci\\b)\\w+", "class "],
    },
    "word_counter": {
        "principle": "Verification-First Workflow",
        "prompt": (
            "Write a Python function `count_words(text: str) -> dict` that counts word frequencies. "
            "Return ONLY the function code. Words are case-insensitive, split by whitespace, ignore punctuation."
        ),
        "assertions": [
            {"input": "hello world hello", "expected": {"hello": 2, "world": 1}},
            {"input": "Hello, World! Hello.", "expected": {"hello": 2, "world": 1}},
            {"input": "", "expected": {}},
            {"input": "one", "expected": {"one": 1}},
        ],
        "forbidden": ["def (?!count_words\\b)\\w+", "class "],
    },
    "surgical_fix": {
        "principle": "Surgical & Precise Changes",
        "prompt": (
            "You have this buggy function:\n"
            "```python\ndef calculate_average(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)\n```\n"
            "Fix ONLY the bug (empty list causes ZeroDivisionError). "
            "Return ONLY the corrected function code. Do NOT add type hints, docstrings, or anything else. "
            "Do NOT rename the function."
        ),
        "assertions": [
            {"input": [1, 2, 3], "expected": 2.0},
            {"input": [], "expected": 0.0},
            {"input": [5], "expected": 5.0},
        ],
        "forbidden": [
            "def (?!calculate_average\\b)\\w+",
            "import ",
            "from ",
            "class ",
            "typing",
        ],
    },
    "temperature_converter": {
        "principle": "Simplicity & Minimum Viable",
        "prompt": (
            "Write a Python function `celsius_to_fahrenheit(celsius: float) -> float` "
            "that converts Celsius to Fahrenheit. Return ONLY the function code. Formula: F = C * 9/5 + 32."
        ),
        "assertions": [
            {"input": 0, "expected": 32.0},
            {"input": 100, "expected": 212.0},
            {"input": -40, "expected": -40.0},
            {"input": 37, "expected": 98.6},
        ],
        "forbidden": ["def (?!celsius_to_fahrenheit\\b)\\w+", "class ", "import "],
    },
    "secrets_check": {
        "principle": "Security-Aware Development",
        "prompt": (
            "Write a Python function `get_api_key() -> str` that reads an API key from the environment "
            "variable `MY_API_KEY`. If the env var is not set, raise ValueError. "
            "Return ONLY the function code. Never hardcode API keys or secrets."
        ),
        "assertions": [
            {"input": "", "expected": "placeholder"},
        ],
        "forbidden": [
            "sk-[a-zA-Z0-9]{10,}",
            "Bearer [A-Za-z0-9]{10,}",
            "[a-zA-Z0-9]{32,}",
        ],
    },
}


def generate(count: int = 30, stratified: bool = True) -> List[TestCase]:
    """Generate concrete tests.

    When stratified=True, distributes tests evenly across subtask types.
    Each subtask type gets roughly count/len(SUBTASKS) tests.
    """
    tests = []
    task_names = list(SUBTASKS.keys())

    if stratified:
        per_type = max(1, count // len(task_names))
        for task_name in task_names:
            task = SUBTASKS[task_name]
            for i in range(per_type):
                tests.append(_make_test(task_name, task, i, per_type))
        # Pad remaining to reach count
        extra = count - len(tests)
        for i in range(extra):
            task_name = task_names[i % len(task_names)]
            task = SUBTASKS[task_name]
            tests.append(_make_test(task_name, task, len(tests), 0))
    else:
        for i in range(count):
            task_name = task_names[i % len(task_names)]
            task = SUBTASKS[task_name]
            tests.append(_make_test(task_name, task, i, 0))

    return tests


def _make_test(task_name: str, task: Dict, idx: int, _per_type: int) -> TestCase:
    prompt = (
        f"Task: {task['prompt']}\n\n"
        f"Apply the specification principle: '{task['principle']}'. "
        f"Return ONLY the function code in a markdown python block."
    )
    return TestCase(
        id=f"concrete-{task_name}-{idx:03d}",
        category="concrete",
        sub_category=task_name,
        prompt=prompt,
        expected_behaviors=[task["principle"], "produces executable code"],
        good_response="```python\ndef func():\n    pass\n```",
        bad_response="Here's how I would write it... [no actual code]",
        rubric_target={"Scope Discipline": 4, "Simplicity": 4, "Verification": 4},
        concrete_assertions=task["assertions"],
        forbidden_patterns=task["forbidden"],
    )


def get_subtask_names() -> List[str]:
    return list(SUBTASKS.keys())
