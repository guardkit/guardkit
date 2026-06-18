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


# A real conftest ImportError (the reproduction): pytest exits non-(0,1) with a
# collection error and NO test ever executes.
_CONFTEST_IMPORT_ERR = (
    "ImportError while loading conftest "
    "'/wt/tests/conftest.py'.\n"
    "tests/conftest.py:6: in <module>\n"
    "    import pytest_asyncio\n"
    "E   ModuleNotFoundError: No module named 'pytest_asyncio'\n"
)


class TestSignalAbsentClassifier:
    def test_conftest_import_error_is_absent(self, tmp_path):
        """exit-4 + 'ImportError while loading conftest' -> signal_absent=True
        (the TASK-SMOKE-REDACT01 case). Must NOT be a 'ran-and-failed' result."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(4, stdout=_CONFTEST_IMPORT_ERR)):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is True

    def test_collection_error_phrase_is_absent(self, tmp_path):
        """A generic collection error (e.g. exit-2 'errors during collection')
        is absent — zero tests executed."""
        v = _make_validator(tmp_path)
        out = "!!! Interrupted: 1 error during collection !!!\nerrors during collection\n"
        with patch("subprocess.run", return_value=_proc(2, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is True

    def test_runner_absent_still_absent(self, tmp_path):
        """Regression guard: 'No module named pytest' (runner absent) stays absent."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stderr="No module named pytest")):
            r = v.run_independent_tests()
        assert r.signal_absent is True

    def test_no_tests_collected_exit5_still_absent(self, tmp_path):
        """Regression guard: exit-5 (no tests collected) stays absent."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(5, stdout="no tests ran")):
            r = v.run_independent_tests()
        assert r.signal_absent is True

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
