"""Pytest-summary-line verdict for the SDK independent-test path
(TASK-FIX-COACHTRES01).

The capture fix surfaces the *real* pytest output to the Coach's SDK-path
pass/fail determination. The legacy heuristic scanned the WHOLE output for the
substrings "error"/"failed"/"failure" — which false-positives on a *passing*
run whose verbose test names or ``--cov`` file paths contain those words. The
FEAT-HARV TASK-HARV-006 false-block (``15 passed in 2.75s`` read as a failure
because a passing ``test_..._displays_error`` and a covered
``*_error_messages.py`` path matched) motivates these tests.

``_verdict_from_pytest_summary`` derives the verdict from the pytest *summary
line* (real counts) instead, falling back to the substring heuristic only when
no summary line is present.
"""

from __future__ import annotations

import os

# Harness-touching import — pin SDK so importing the validator does not resolve
# the LangGraph substrate at import time (the pure classmethod under test is
# substrate-independent).
os.environ.setdefault("GUARDKIT_HARNESS", "sdk")

from guardkit.orchestrator.quality_gates.coach_validator import (  # noqa: E402
    CoachValidator,
)

_verdict = CoachValidator._verdict_from_pytest_summary


# ----------------------------------------------------------------------
# The FEAT-HARV TASK-HARV-006 reproducer
# ----------------------------------------------------------------------

# A realistic passing run whose output contains TWO incidental "error"
# substrings (a passing test whose name says "error", and a covered file path
# with "error" in it) plus a --cov table — the exact shape that false-blocked.
_FEAT_HARV_006_OUTPUT = """\
============================= test session starts ==============================
collected 15 items

tests/acceptance/test_harvest_contract.py::test_publish_roundtrip passed [  6%]
tests/acceptance/test_harvest_contract.py::test_oversized_rejection_cli_displays_error passed [ 60%]
tests/acceptance/test_harvest_contract.py::test_taxonomy_subjects passed [100%]

---------- coverage: platform linux, python 3.11 -----------
Name                                                   Stmts   Miss  Cover
--------------------------------------------------------------------------
installer/core/lib/orchestrator_error_messages.py        120    120     0%
guardkit/memory/harvest_walker.py                         44      0   100%
--------------------------------------------------------------------------
TOTAL                                                  12178  12162     1%

============================== 15 passed in 2.75s ==============================
"""


def test_feat_harv_006_passing_run_with_error_substrings_is_pass() -> None:
    """The exact false-block: 15 passed, but 'error' appears twice incidentally."""
    # Sanity: the substrings that fooled the old heuristic ARE present.
    assert "error" in _FEAT_HARV_006_OUTPUT.lower()
    assert _verdict(_FEAT_HARV_006_OUTPUT) is True


# ----------------------------------------------------------------------
# Genuine failures must still be False
# ----------------------------------------------------------------------


def test_one_failed_is_fail() -> None:
    out = "==================== 1 failed, 14 passed in 0.30s ====================="
    assert _verdict(out) is False


def test_collection_errors_is_fail() -> None:
    out = "======================== 2 errors in 1.00s ========================="
    assert _verdict(out) is False


def test_failed_and_errors_is_fail() -> None:
    out = "============= 1 failed, 1 error, 12 passed in 0.50s ============="
    assert _verdict(out) is False


# ----------------------------------------------------------------------
# Passing variants
# ----------------------------------------------------------------------


def test_passed_with_warnings_is_pass() -> None:
    out = "================= 15 passed, 2 warnings in 2.75s ================="
    assert _verdict(out) is True


def test_single_passed_is_pass() -> None:
    out = "===================== 1 passed in 0.01s ====================="
    assert _verdict(out) is True


# ----------------------------------------------------------------------
# Indeterminate -> None (caller falls back to the substring heuristic)
# ----------------------------------------------------------------------


def test_narration_only_is_none() -> None:
    assert _verdict("I'll run the test command and show you the full output.") is None


def test_empty_is_none() -> None:
    assert _verdict("") is None
    assert _verdict("No output") is None


def test_no_tests_ran_is_none() -> None:
    out = "===================== no tests ran in 0.01s ====================="
    assert _verdict(out) is None


def test_skipped_only_is_none() -> None:
    out = "===================== 5 skipped in 0.10s ====================="
    assert _verdict(out) is None


def test_last_summary_line_wins() -> None:
    """If multiple summary-shaped lines exist, the final pytest summary wins."""
    out = (
        "==================== 3 failed in 0.10s =====================\n"
        "...re-run after fix...\n"
        "==================== 18 passed in 0.20s ====================="
    )
    assert _verdict(out) is True
