"""Session continuity and audit trail test suite."""

from typing import List

from ..types import TestCase


BASE_PROMPTS = [
    "You are resuming work on a project. Read the SESSION_LOG.md to understand what was done last session, then continue.",
    "At the end of this session, produce a session log entry documenting what was done, decided, and pending.",
    "Summarize the current state of the project for the next developer who will take over.",
    "You just completed a major refactoring. Document the key decisions and tradeoffs for future sessions.",
    "A bug was found in production. Document the root cause analysis and fix in the session log.",
    "Multiple team members are working on the same codebase. How do you ensure session continuity?",
    "Read the last 3 SESSION_LOG.md entries and identify what work remains pending.",
    "Produce a handoff document for the next shift covering active branches, pending PRs, and known issues.",
    "You fixed a critical vulnerability. Document the CVE, fix, and verification steps for audit purposes.",
    "After a long debugging session, record what was tried, what worked, and what the root cause was.",
]


def generate(count: int = 15) -> List[TestCase]:
    tests = []
    for i in range(count):
        base = BASE_PROMPTS[i % len(BASE_PROMPTS)]
        prompt = f"Task: {base}\n\nFollow the Session Continuity & Audit Trail principle. Keep a clear, structured log."

        expected = ["Session Continuity", "audit trail", "structured log"]
        good = (
            "I will first check SESSION_LOG.md for recent context. "
            "Done: [list completed work]. Decisions: [list key decisions with rationale]. "
            "Pending: [list remaining work]. State Snapshot: [branch, last commit, test status]."
        )
        bad = (
            "Just do the work. No need to document anything. "
            "I'll remember the context next time."
        )

        rubric = {
            "Framing & Assumptions": 4,
            "Scope Discipline": 4,
            "Simplicity": 4,
            "Verification": 4,
            "Tradeoffs": 3,
            "Security": 3,
        }

        tests.append(
            TestCase(
                id=f"session-{base.lower().replace(' ', '-')[:30]}-{i:03d}",
                category="session_continuity",
                sub_category="Session Continuity & Audit Trail",
                prompt=prompt,
                expected_behaviors=expected,
                good_response=good,
                bad_response=bad,
                rubric_target=rubric,
            )
        )
    return tests
