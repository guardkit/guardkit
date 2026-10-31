"""TASK-ABFIX-011 — gated per-test ``--timeout`` in the Coach's isolated pytest run.

A single hanging test otherwise consumes the whole Coach subprocess budget and
yields ``tests_run=0`` (no per-test attribution). Injecting
``--timeout N --timeout-method signal`` marks the *specific* hung test FAILED
while the others still run. Injection is TRIPLE-gated (operator flag, Python
stack, plugin resolvable) so it can never become the harness-wide false-fail an
*unconditional* ``--timeout`` would be — the already-reverted FEAT-FMDR-003
regression replayed harness-wide.

Since 31 October 2026 only the opt-in SDK test path injects it; the isolated
copy, the standard subprocess rewrite and the usage-error reading went (a
declared command runs exactly as declared). Covers the gating, the probe and
the SDK pin, and the constraints in
``.claude/rules/stack-plugin-architecture.md`` and
``.claude/rules/absence-of-failure-is-not-success.md``.

Coverage target: >=85%
"""

import subprocess
import sys
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
# The SDK path's pin (the opt-in SDK test path still pins pytest)
# ============================================================================


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
