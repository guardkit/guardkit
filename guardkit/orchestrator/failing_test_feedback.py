"""Telling the Player which tests failed (8 October 2026).

Build FEAT-895D spent three turns on a task whose only problem was one failing
test, and the Player was never told which one. The test phase had named it in
``specialist_results.json``; the quality-gate feedback said only "Tests did not
pass during task-work execution"; and the turn's feedback was then cut to its
first three issues, all of them honesty warnings, so even that line was lost.
The coder's ``must_fix`` list for the next turn was empty.

This module is the small contract that carries the names through, shared by
the places that touch them, so none of them has its own copy:

* The deterministic test phase (``specialist_invocations``) records the
  failing tests it saw in its phase-4 record: the newly failing ones when it
  compared the run with the base, otherwise every failing one, read by the
  same extraction the comparison uses. It records how many there were, and
  which of the two lists it is (:data:`FAILING_TESTS_BASIS_NEW` or
  :data:`FAILING_TESTS_BASIS_OBSERVED`).
* ``AgentInvoker._inject_specialist_records_into_task_work_results`` copies
  the names, their total and basis, and the test phase's one-line account of
  the failure, into ``task_work_results.json`` (the ``QG_*`` keys).
* ``CoachValidator._feedback_from_gates`` puts them into the ``must_fix``
  test-failure issue, through :func:`describe_failing_tests`.
* :func:`phase_4_ran_and_failed` is the one test, used by the merge, of
  whether the test phase produced evidence (a failure) or did not run at all.
  The merge marks a ran-and-failed record with :data:`RAN_AND_FAILED`, and the
  Coach then does not call it a missing-evidence ("substrate") failure.
* ``AutoBuildOrchestrator._extract_feedback`` writes must-fix issues first,
  each starting with :data:`MUST_FIX_MARKER`, and
  ``AgentInvoker._parse_coach_feedback`` reads them back into the feedback
  file's ``must_fix`` list with :func:`must_fix_items`.

Tool-agnostic by design: nothing here parses test output. The names are
whatever the test phase already reported, in its own words, and when it could
read none the feedback says so.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

# Keys in task_work_results.json's ``quality_gates`` block.
QG_FAILING_TESTS = "failing_tests"
QG_FAILING_TESTS_TOTAL = "failing_tests_total"
QG_FAILING_TESTS_BASIS = "failing_tests_basis"
QG_FAILURE_SUMMARY = "failure_summary"

# Keys the test phase's own record (specialist_results.json, phase_4) carries
# when its run failed: the failing tests it saw, how many in all, and which
# ones they are (FAILING_TESTS_BASIS_*). The record uses the same key names.
PHASE_4_FAILING_TESTS = QG_FAILING_TESTS
PHASE_4_FAILING_TESTS_TOTAL = QG_FAILING_TESTS_TOTAL
PHASE_4_FAILING_TESTS_BASIS = QG_FAILING_TESTS_BASIS

# Which failing tests a record names.
# * NEW: the run was compared with what was already failing before the build
#   started, and these are the ones that were not (the ones charged).
# * OBSERVED: no such comparison was made (nothing was on record about the
#   base, or the run was of the task's own tests), so these are every failing
#   test the run reported.
FAILING_TESTS_BASIS_NEW = "new since the base"
FAILING_TESTS_BASIS_OBSERVED = "observed"

# How many names the test phase's record keeps; the total is always kept.
FAILING_TESTS_RECORDED = 50

# How many names the feedback shows; the full count is always said.
FAILING_TESTS_SHOWN = 10

# How long the one-line account of the failure may be.
FAILURE_SUMMARY_LIMIT = 240

# Set on the orchestrator's phase-4 record in agent_invocations when the test
# phase ran and tests failed.
RAN_AND_FAILED = "ran_and_failed"

# The same fact in task_work_results.json's ``quality_gates`` block, set (or
# removed) by the specialist-record merge on every turn, so the gate's
# feedback can tell a test run that failed from one that did not.
QG_TEST_PHASE_RAN_AND_FAILED = "test_phase_ran_and_failed"

# The longest a must-fix item read back from the feedback text may be.
MUST_FIX_ITEM_LIMIT = 2000

# Starts each must-fix line of the feedback text the Player is given.
MUST_FIX_MARKER = "MUST FIX: "


def phase_4_ran_and_failed(block: object) -> bool:
    """Did the test phase run the tests and see at least one fail?

    True only for a ``failed`` phase-4 record that is not an absent signal and
    reports a positive count of failing tests. That is evidence about the
    code — the opposite of a test phase that hung, crashed or ran nothing,
    which reports ``failed`` with no failing tests and is an absent signal
    about the code. Reads only the counts the test phase itself wrote.
    """
    if not isinstance(block, dict):
        return False
    if block.get("status") != "failed" or block.get("signal_absent"):
        return False
    failed = block.get("tests_failed")
    return isinstance(failed, int) and not isinstance(failed, bool) and failed > 0


def describe_failing_tests(
    failing_tests: Optional[Sequence[str]],
    failure_summary: Optional[str],
    *,
    total: Optional[int] = None,
    basis: Optional[str] = None,
    test_phase_failed: bool = False,
) -> str:
    """The words added to a test-failure issue, or ``""`` when there are none.

    Names the first :data:`FAILING_TESTS_SHOWN` failing tests and says how many
    there are in all (``total`` when the record kept fewer names than it saw),
    then the test phase's own one-line account of the failure. With
    ``basis`` :data:`FAILING_TESTS_BASIS_NEW` the tests are called newly
    failing. When the test phase ran and failed but named no test
    (``test_phase_failed`` with no names), it says so, rather than saying
    nothing: the test tool's output was not one the factory reads names from.
    """
    names = [str(n) for n in (failing_tests or []) if n]
    parts: List[str] = []
    if names:
        shown = names[:FAILING_TESTS_SHOWN]
        count = max(len(names), total if isinstance(total, int) else 0)
        noun = "test" if count == 1 else "tests"
        if basis == FAILING_TESTS_BASIS_NEW:
            label = (
                f"{count} newly failing {noun} (not failing before this "
                f"build started)"
            )
        else:
            label = f"{count} failing {noun}"
        text = f"{label}: " + "; ".join(shown)
        if count > len(shown):
            text += f"; and {count - len(shown)} more"
        parts.append(text + ".")
    elif test_phase_failed:
        parts.append(
            "The test run did not name its failing tests in a form the "
            "factory can read, so none are listed here."
        )
    summary = " ".join(str(failure_summary or "").split())
    if summary:
        parts.append(f"What the test run said: {summary[:FAILURE_SUMMARY_LIMIT]}")
    return " ".join(parts)


def must_fix_items(feedback_text: str) -> List[str]:
    """Read the must-fix items back out of the feedback text.

    An item is a line that starts with ``"- "`` followed by
    :data:`MUST_FIX_MARKER`, together with every line after it up to the next
    issue (a line starting ``"- "``), the ``"... and N more issues"`` line, or
    a blank line (which is where text appended after the issues begins). So a
    multi-line description or test output is kept whole, bounded to
    :data:`MUST_FIX_ITEM_LIMIT` characters. The marker itself is left out of
    what comes back. Text with no marked line gives an empty list, which is
    what every feedback written before this module gave.
    """
    items: List[str] = []
    current: Optional[List[str]] = None
    prefix = f"- {MUST_FIX_MARKER}"

    def _close() -> None:
        text = "\n".join(current or []).strip()
        if text:
            items.append(text[:MUST_FIX_ITEM_LIMIT])

    for line in (feedback_text or "").splitlines():
        if line.startswith(prefix):
            if current is not None:
                _close()
            current = [line[len(prefix):]]
        elif current is None:
            continue
        elif (
            line.startswith("- ")
            or line.startswith("... and ")
            or not line.strip()
        ):
            _close()
            current = None
        else:
            current.append(line[2:] if line.startswith("  ") else line)
    if current is not None:
        _close()
    return items
