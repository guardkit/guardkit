"""Regression tests for the SDK independent-test narration→absent guard
(TASK-FIX-COACHNARR01).

Defect (FEAT-HARV TASK-HARV-003): the SDK independent-test path
(``CoachValidator._run_tests_via_sdk``, the default ``coach_test_execution=sdk``)
does not receive the Bash tool's stdout — the SDK harness does not surface it as
a ToolResultEvent, so the captured ``output_text`` is the COACH AGENT's assistant
text. When the agent merely narrated ("I'll run the test command and show you the
full output.") the heuristic found no success marker and no failure marker, yet
returned ``tests_passed=False`` with ``signal_absent=False`` — a false
ran-and-failed verdict. The Coach treated that as authoritative and overrode the
deterministic subprocess oracle, which actually ran pytest and passed (8601/8601)
every turn, blocking the otherwise-complete walker to ``max_turns_exceeded``.

The fix: a captured output with NEITHER a pytest success NOR a failure marker is
an ABSENT signal (``signal_absent=True``), never a ran-and-failed verdict — per
absence-of-failure-is-not-success.md it never blocks and never counts as a pass,
so the Coach falls back to the deterministic subprocess result.
"""
from __future__ import annotations

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


_NARRATION = "I'll run the test command and show you the full output."


class TestClassifySdkHeuristicOutput:
    def test_feat_harv_narration_is_absent(self) -> None:
        """The exact FEAT-HARV TASK-HARV-003 capture: agent narration with no
        pytest markers is ABSENT, not a failure."""
        tests_passed, signal_absent = CoachValidator._classify_sdk_heuristic_output(
            _NARRATION
        )
        assert tests_passed is False
        assert signal_absent is True

    @pytest.mark.parametrize(
        "text",
        ["", "   ", "No output", "I will now run pytest for you."],
    )
    def test_no_marker_text_is_absent(self, text: str) -> None:
        assert CoachValidator._classify_sdk_heuristic_output(text) == (False, True)

    def test_zero_collected_is_absent(self) -> None:
        """`collected 0 items / no tests ran` carries no pass/fail marker —
        absent (zero-cardinality), consistent with absence-of-failure."""
        assert CoachValidator._classify_sdk_heuristic_output(
            "collected 0 items\n\nno tests ran in 0.01s"
        ) == (False, True)

    def test_real_pass_is_passed_not_absent(self) -> None:
        assert CoachValidator._classify_sdk_heuristic_output(
            "45 passed in 0.13s"
        ) == (True, False)

    def test_real_failure_is_failed_not_absent(self) -> None:
        """A genuine failure must stay a ran-and-failed verdict — NOT masked as
        absent. This is the must-not-regress direction."""
        tests_passed, signal_absent = CoachValidator._classify_sdk_heuristic_output(
            "FAILED tests/test_x.py::test_y - AssertionError: assert False"
        )
        assert tests_passed is False
        assert signal_absent is False

    def test_mixed_output_fails_and_is_not_absent(self) -> None:
        """Failures present alongside passes -> failure wins, not absent."""
        assert CoachValidator._classify_sdk_heuristic_output(
            "3 passed, 1 failed in 0.20s"
        ) == (False, False)

    def test_error_marker_is_failure_not_absent(self) -> None:
        assert CoachValidator._classify_sdk_heuristic_output(
            "ERROR collecting tests/test_x.py"
        ) == (False, False)
