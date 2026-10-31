"""TASK-AB-PERTASKFG01 fix #4 — ``run_independent_tests`` absent-signal classifier.

A pytest *collection / conftest import* failure means ZERO tests executed, so
the Coach's independent oracle produced NO verdict on the Player's code. That is
an ABSENT signal (``signal_absent=True``), not a "ran-and-failed" result —
otherwise it disarms the deterministic ``_reconcile_absent_independent_test_signal``
backstop and lets the LLM Coach rationalise the env error and approve an
unverified deliverable (the TASK-SMOKE-REDACT01 false-green, 2026-06-18).

Instance of ``.claude/rules/absence-of-failure-is-not-success.md``.
"""

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


def _make_validator(tmp_path: Path, test_cmd: str = "pytest tests/ -v") -> CoachValidator:
    validator = CoachValidator(
        worktree_path=tmp_path, task_id="TASK-AB-PERTASKFG01", test_command=test_cmd
    )
    validator._coach_test_execution = "subprocess"
    return validator


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestSignalAbsentClassifier:
    """31 October 2026: pytest's own phrases and exit codes (conftest import
    errors, collection errors, "No module named pytest", exit 5) are no
    longer read for any command; those tests were removed with the readings.
    What stays: a run that ran is its exit code."""

    def test_genuine_test_failure_is_not_absent(self, tmp_path):
        """No over-reach: tests that RAN and failed (exit-1, test summary) are a
        real failure, NOT an absent signal — the guard must not mask them."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stdout="2 failed, 8 passed in 1.2s")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False

    def test_passing_run_is_not_absent(self, tmp_path):
        """Happy path: a passing run is neither failed nor absent."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(0, stdout="10 passed in 0.9s")):
            r = v.run_independent_tests()
        assert r.tests_passed is True
        assert r.signal_absent is False
