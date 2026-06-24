"""TASK-ABFIX-011 — gated per-test ``--timeout`` in the Coach's isolated pytest run.

A single hanging test otherwise consumes the whole Coach subprocess budget and
yields ``tests_run=0`` (no per-test attribution). Injecting
``--timeout N --timeout-method signal`` marks the *specific* hung test FAILED
while the others still run. Injection is TRIPLE-gated (operator flag, Python
stack, plugin resolvable) so it can never become the harness-wide false-fail an
*unconditional* ``--timeout`` would be — the already-reverted FEAT-FMDR-003
regression replayed harness-wide.

Covers all four surfaces (SDK pin, isolated/parallel subprocess, standard
subprocess, absent classifier) and the constraints in
``.claude/rules/stack-plugin-architecture.md`` and
``.claude/rules/absence-of-failure-is-not-success.md``.

Coverage target: >=85%
"""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    _DEFAULT_COACH_PER_TEST_TIMEOUT_S,
)


def _make_validator(
    tmp_path: Path,
    test_cmd: str = "pytest tests/ -v",
    wave_size: int = 1,
) -> CoachValidator:
    validator = CoachValidator(
        worktree_path=tmp_path,
        task_id="TASK-ABFIX-011",
        test_command=test_cmd,
        wave_size=wave_size,
    )
    validator._coach_test_execution = "subprocess"
    return validator


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ============================================================================
# 1. Gate + argv construction (constraints 1 + 2)
# ============================================================================


class TestTimeoutArgvGating:
    def test_argv_injected_when_python_and_available(self, tmp_path, monkeypatch):
        """Python stack + plugin available + not disabled → full argv fragment."""
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", raising=False)
        v = _make_validator(tmp_path)
        v._pytest_timeout_available_cache = True  # avoid the probe
        assert v._active_stack_profile is None  # Python
        assert v._pytest_timeout_argv() == [
            "--timeout",
            str(_DEFAULT_COACH_PER_TEST_TIMEOUT_S),
            "--timeout-method",
            "signal",
        ]

    def test_argv_empty_for_non_python_stack(self, tmp_path):
        """A non-Python stack profile yields NO --timeout arg (AC #3).

        stack-plugin-architecture.md: a Python-only arg must never reach a
        .NET/JS/Go whole_suite_command.
        """
        v = _make_validator(tmp_path)
        v._pytest_timeout_available_cache = True  # plugin present, but...
        v._active_stack_profile = MagicMock()  # ...a non-Python stack is active
        assert v._pytest_timeout_argv() == []

    def test_argv_empty_when_plugin_absent(self, tmp_path):
        """Plugin not resolvable → no injection (AC #2 — process-level fallback)."""
        v = _make_validator(tmp_path)
        v._pytest_timeout_available_cache = False
        assert v._pytest_timeout_argv() == []

    @pytest.mark.parametrize("flag", ["0", "false", "off", "no", "OFF", "False"])
    def test_argv_empty_when_operator_disabled(self, tmp_path, monkeypatch, flag):
        """Operator escape hatch: GUARDKIT_COACH_PYTEST_TIMEOUT=0 disables it."""
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT", flag)
        v = _make_validator(tmp_path)
        v._pytest_timeout_available_cache = True
        assert v._pytest_timeout_argv() == []

    def test_seconds_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", "5")
        v = _make_validator(tmp_path)
        assert v._per_test_timeout_seconds() == 5

    @pytest.mark.parametrize("bad", ["not-an-int", "-3", "0"])
    def test_seconds_env_invalid_falls_back_to_default(self, tmp_path, monkeypatch, bad):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", bad)
        v = _make_validator(tmp_path)
        assert v._per_test_timeout_seconds() == _DEFAULT_COACH_PER_TEST_TIMEOUT_S

    def test_method_default_is_signal(self, tmp_path, monkeypatch):
        """signal is the default: it lets the session continue so the OTHER
        tests still run (the per-test attribution the AC requires)."""
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", raising=False)
        v = _make_validator(tmp_path)
        assert v._pytest_timeout_method() == "signal"

    def test_method_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", "thread")
        v = _make_validator(tmp_path)
        assert v._pytest_timeout_method() == "thread"

    def test_method_invalid_env_falls_back_to_signal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", "garbage")
        v = _make_validator(tmp_path)
        assert v._pytest_timeout_method() == "signal"


# ============================================================================
# 2. Availability probe + caching (constraint 1b)
# ============================================================================


class TestProbe:
    def test_in_process_probe_when_interpreter_is_sys_executable(self, tmp_path):
        """No pinned venv → interp == sys.executable → in-process find_spec,
        no subprocess (so it never perturbs subprocess.run mocks)."""
        v = _make_validator(tmp_path)
        assert v._pytest_interpreter() == sys.executable
        with patch("subprocess.run") as mock_run, patch(
            "importlib.util.find_spec", return_value=object()
        ):
            assert v._probe_pytest_timeout() is True
        mock_run.assert_not_called()

    def test_in_process_probe_absent(self, tmp_path):
        v = _make_validator(tmp_path)
        with patch("importlib.util.find_spec", return_value=None):
            assert v._probe_pytest_timeout() is False

    def test_subprocess_probe_when_distinct_venv(self, tmp_path):
        """A distinct pinned venv → out-of-process find_spec probe; rc0 → True."""
        v = _make_validator(tmp_path)
        v._venv_python = Path("/fake/venv/bin/python")  # != sys.executable
        with patch("subprocess.run", return_value=_proc(0)) as mock_run:
            assert v._probe_pytest_timeout() is True
        mock_run.assert_called_once()
        # Probes the pinned interpreter, not the orchestrator's.
        assert mock_run.call_args.args[0][0] == "/fake/venv/bin/python"

    def test_subprocess_probe_nonzero_is_absent(self, tmp_path):
        v = _make_validator(tmp_path)
        v._venv_python = Path("/fake/venv/bin/python")
        with patch("subprocess.run", return_value=_proc(1)):
            assert v._probe_pytest_timeout() is False

    def test_subprocess_probe_error_is_absent(self, tmp_path):
        """Any probe error (OSError / timeout) → fail toward NO injection."""
        v = _make_validator(tmp_path)
        v._venv_python = Path("/fake/venv/bin/python")
        with patch("subprocess.run", side_effect=OSError("boom")):
            assert v._probe_pytest_timeout() is False

    def test_availability_is_cached(self, tmp_path):
        v = _make_validator(tmp_path)
        with patch.object(v, "_probe_pytest_timeout", return_value=True) as mock_probe:
            assert v._pytest_timeout_available() is True
            assert v._pytest_timeout_available() is True
        mock_probe.assert_called_once()  # probed once, then cached


# ============================================================================
# 3. Injection at all three pytest construction sites (AC #5 — all surfaces)
# ============================================================================


class TestStandardSubprocessInjection:
    def test_injected_into_standard_subprocess_cmd(self, tmp_path):
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v --tb=short")
        v._pytest_timeout_available_cache = True
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert "--timeout" in cmd
        assert "--timeout-method" in cmd
        assert "signal" in cmd
        # original args preserved, interpreter still pinned first
        assert cmd[0] == sys.executable and cmd[1] == "-m" and cmd[2] == "pytest"
        assert "--tb=short" in cmd

    def test_not_injected_when_unavailable(self, tmp_path):
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v")
        v._pytest_timeout_available_cache = False
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        assert "--timeout" not in mock_run.call_args.args[0]


class TestIsolatedParallelInjection:
    def test_injected_into_isolated_parallel_cmd(self, tmp_path):
        """wave_size > 1 → _run_isolated_tests path also injects (the easy-to-miss
        4th injection site, ABFIX-010 GAP 3)."""
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v", wave_size=2)
        v._pytest_timeout_available_cache = True
        assert v.is_parallel is True
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert "--timeout" in cmd and "--timeout-method" in cmd

    def test_not_injected_when_unavailable_isolated(self, tmp_path):
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v", wave_size=2)
        v._pytest_timeout_available_cache = False
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        assert "--timeout" not in mock_run.call_args.args[0]


class TestSdkPinInjection:
    def test_pin_pytest_command_appends_timeout(self, tmp_path):
        v = _make_validator(tmp_path)
        v._venv_python = Path(sys.executable)  # pinned venv (not None)
        v._pytest_timeout_available_cache = True
        pinned = v._pin_pytest_command("pytest tests/ -v")
        assert "--timeout" in pinned and "--timeout-method signal" in pinned
        assert pinned.startswith(f"{sys.executable} -m pytest tests/ -v")

    def test_pin_pytest_command_bare_pytest(self, tmp_path):
        v = _make_validator(tmp_path)
        v._venv_python = Path(sys.executable)
        v._pytest_timeout_available_cache = True
        pinned = v._pin_pytest_command("pytest")
        assert pinned == f"{sys.executable} -m pytest --timeout 60 --timeout-method signal"

    def test_pin_pytest_command_no_venv_no_injection(self, tmp_path):
        """No pinned venv → command passes through unchanged (probe interpreter
        would not match the PATH-resolved run interpreter)."""
        v = _make_validator(tmp_path)
        v._venv_python = None
        v._pytest_timeout_available_cache = True
        assert v._pin_pytest_command("pytest tests/ -v") == "pytest tests/ -v"

    def test_pin_pytest_command_no_injection_when_unavailable(self, tmp_path):
        v = _make_validator(tmp_path)
        v._venv_python = Path(sys.executable)
        v._pytest_timeout_available_cache = False
        assert v._pin_pytest_command("pytest tests/ -v") == (
            f"{sys.executable} -m pytest tests/ -v"
        )


# ============================================================================
# 4. Defence-in-depth: --timeout usage error → signal_absent (constraint 3)
# ============================================================================


class TestUsageErrorClassifier:
    def test_predicate_matches_unrecognized_timeout(self):
        assert (
            CoachValidator._is_pytest_timeout_usage_error(
                4, "error: unrecognized arguments: --timeout 60"
            )
            is True
        )

    def test_predicate_rejects_other_rc4(self):
        # rc-4 conftest import error is NOT a --timeout usage error
        assert (
            CoachValidator._is_pytest_timeout_usage_error(
                4, "ImportError while loading conftest"
            )
            is False
        )

    def test_predicate_rejects_rc1_with_timeout_text(self):
        # only rc-4 counts; a genuine failure that happens to mention --timeout
        # must not be classified as a usage error
        assert (
            CoachValidator._is_pytest_timeout_usage_error(
                1, "1 failed; note --timeout in output"
            )
            is False
        )

    def test_standard_path_usage_error_is_absent(self, tmp_path):
        """rc-4 'unrecognized arguments: --timeout' on the standard path →
        signal_absent=True (ABFIX-010 then carries it as None, fed back)."""
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v")
        v._pytest_timeout_available_cache = True
        err = "ERROR: usage: pytest [options]\nunrecognized arguments: --timeout 60"
        with patch("subprocess.run", return_value=_proc(4, stderr=err)):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is True

    def test_isolated_path_usage_error_is_absent(self, tmp_path):
        """Same on the parallel-wave isolated path (parity — AC #5)."""
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v", wave_size=2)
        v._pytest_timeout_available_cache = True
        err = "unrecognized arguments: --timeout 60"
        with patch("subprocess.run", return_value=_proc(4, stderr=err)):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is True

    def test_genuine_failure_not_masked(self, tmp_path):
        """A real test failure (rc-1, test summary) stays signal_absent=False —
        the narrow usage-error match must never mask it."""
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v")
        v._pytest_timeout_available_cache = True
        with patch("subprocess.run", return_value=_proc(1, stdout="2 failed, 8 passed in 1.2s")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False


# ============================================================================
# 5. Real-execution behaviour (AC #6, #7) — needs the real plugins
# ============================================================================

_HAS_TIMEOUT = importlib.util.find_spec("pytest_timeout") is not None
_HAS_ASYNCIO = importlib.util.find_spec("pytest_asyncio") is not None

_THREE_TESTS_ONE_HANGS = textwrap.dedent(
    """
    import time
    def test_a_fast_before(): assert True
    def test_b_hangs(): time.sleep(30)
    def test_c_fast_after(): assert True
    """
)


@pytest.mark.skipif(not _HAS_TIMEOUT, reason="pytest-timeout not installed")
class TestRealHungTest:
    """End-to-end: a real hung test is named-FAILED while the others still run.

    Coach pins the interpreter to sys.executable (no worktree venv) which has
    pytest + pytest-timeout, so the in-process probe resolves and injection
    fires. Uses ``coach_test_execution='subprocess'`` so no harness/SDK is
    touched (AC #8 — CI-safe without GUARDKIT_HARNESS).
    """

    def _worktree(self, tmp_path: Path) -> Path:
        (tmp_path / "test_hang.py").write_text(_THREE_TESTS_ONE_HANGS)
        return tmp_path

    def test_single_wave_hung_test_is_attributed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", "2")
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT", raising=False)
        wt = self._worktree(tmp_path)
        v = _make_validator(wt, test_cmd="pytest test_hang.py -p no:cacheprovider")
        r = v.run_independent_tests()
        # the hung test is named FAILED; the OTHER two ran and passed
        assert r.tests_passed is False
        assert r.signal_absent is False  # it RAN — a real attribution, not absent
        assert "test_b_hangs" in r.raw_output
        assert "2 passed" in r.raw_output

    def test_parallel_wave_hung_test_is_attributed(self, tmp_path, monkeypatch):
        """wave_size=2 → the isolated/parallel path, the 4th injection site."""
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", "2")
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT", raising=False)
        wt = self._worktree(tmp_path)
        v = _make_validator(
            wt, test_cmd="pytest test_hang.py -p no:cacheprovider", wave_size=2
        )
        assert v.is_parallel is True
        r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False
        assert "test_b_hangs" in r.raw_output
        assert "2 passed" in r.raw_output


@pytest.mark.skipif(
    not (_HAS_TIMEOUT and _HAS_ASYNCIO),
    reason="pytest-timeout and pytest-asyncio required",
)
class TestRealAsyncioNotInterrupted:
    """AC #6: --timeout-method=signal must not spuriously interrupt a healthy
    asyncio test (the alarm only fires once a test exceeds the deadline)."""

    def test_fast_asyncio_test_passes_under_signal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS", "5")
        monkeypatch.setenv("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", "signal")
        monkeypatch.delenv("GUARDKIT_COACH_PYTEST_TIMEOUT", raising=False)
        (tmp_path / "pytest.ini").write_text("[pytest]\nasyncio_mode = auto\n")
        (tmp_path / "test_async.py").write_text(
            textwrap.dedent(
                """
                import asyncio
                async def test_quick_async():
                    await asyncio.sleep(0.05)
                    assert True
                """
            )
        )
        v = _make_validator(tmp_path, test_cmd="pytest test_async.py -p no:cacheprovider")
        r = v.run_independent_tests()
        assert r.tests_passed is True, r.raw_output
        assert "1 passed" in r.raw_output
        assert r.signal_absent is False
