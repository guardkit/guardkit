"""Telling the Player which tests failed (8 October 2026).

Build FEAT-895D spent three turns on a task whose only problem was one failing
test, and the Player was never told which one. The test phase had named it in
``specialist_results.json``; the quality-gate feedback said only "Tests did not
pass during task-work execution"; and the turn's feedback was then cut to its
first three issues, all of them honesty warnings, so even that line was lost.
The coder's ``must_fix`` list for the next turn was empty.

This module is the small contract that carries the names through, shared by
the three places that touch them, so none of them has its own copy:

* ``AgentInvoker._inject_specialist_records_into_task_work_results`` copies
  the names the test phase reported, and its one-line account of the failure,
  into ``task_work_results.json`` under :data:`QG_FAILING_TESTS` and
  :data:`QG_FAILURE_SUMMARY`.
* ``CoachValidator._feedback_from_gates`` puts them into the ``must_fix``
  test-failure issue, through :func:`describe_failing_tests`.
* ``AutoBuildOrchestrator._extract_feedback`` writes must-fix issues first,
  each starting with :data:`MUST_FIX_MARKER`, and
  ``AgentInvoker._parse_coach_feedback`` reads them back into the feedback
  file's ``must_fix`` list with :func:`must_fix_items`.

Tool-agnostic by design: nothing here parses test output. The names are
whatever the test phase already reported, in its own words.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

# Keys in task_work_results.json's ``quality_gates`` block.
QG_FAILING_TESTS = "failing_tests"
QG_FAILURE_SUMMARY = "failure_summary"

# How many names the feedback shows; the full count is always said.
FAILING_TESTS_SHOWN = 10

# How long the one-line account of the failure may be.
FAILURE_SUMMARY_LIMIT = 240

# Starts each must-fix line of the feedback text the Player is given.
MUST_FIX_MARKER = "MUST FIX: "


def describe_failing_tests(
    failing_tests: Optional[Sequence[str]],
    failure_summary: Optional[str],
) -> str:
    """The words added to a test-failure issue, or ``""`` when there are none.

    Names the first :data:`FAILING_TESTS_SHOWN` failing tests and says how many
    there are in all, then the test phase's own one-line account of the
    failure. Either part is left out when the test phase did not report it.
    """
    names = [str(n) for n in (failing_tests or []) if n]
    parts: List[str] = []
    if names:
        shown = names[:FAILING_TESTS_SHOWN]
        count = len(names)
        noun = "test" if count == 1 else "tests"
        text = f"{count} failing {noun}: " + "; ".join(shown)
        if count > len(shown):
            text += f"; and {count - len(shown)} more"
        parts.append(text + ".")
    summary = " ".join(str(failure_summary or "").split())
    if summary:
        parts.append(f"What the test run said: {summary[:FAILURE_SUMMARY_LIMIT]}")
    return " ".join(parts)


def must_fix_items(feedback_text: str) -> List[str]:
    """Read the must-fix items back out of the feedback text.

    An item is a line that starts with ``"- "`` followed by
    :data:`MUST_FIX_MARKER`, together with the indented lines under it. The
    marker itself is left out of what comes back. Text with no marked line
    gives an empty list, which is what every feedback written before this
    module gave.
    """
    items: List[str] = []
    current: Optional[List[str]] = None
    prefix = f"- {MUST_FIX_MARKER}"
    for line in (feedback_text or "").splitlines():
        if line.startswith(prefix):
            if current is not None:
                items.append("\n".join(current).strip())
            current = [line[len(prefix):]]
        elif current is not None and line.startswith("  "):
            current.append(line.strip())
        elif current is not None:
            items.append("\n".join(current).strip())
            current = None
    if current is not None:
        items.append("\n".join(current).strip())
    return [item for item in items if item]
