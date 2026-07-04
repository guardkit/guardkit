"""TASK-AB-BASETEMP01 — per-run pytest ``--basetemp`` at every
orchestrator-constructed pytest call site.

Two concurrent autobuild loops raced on pytest's shared per-user
``/tmp/pytest-of-<user>`` basetemp (the FEAT-ABL-005 Coach died on that race
three turns straight). Every pytest argv the ORCHESTRATOR ITSELF constructs
must carry a unique ``--basetemp`` under the system temp dir:

1. Coach standard subprocess independent-test run (``coach_validator.py``).
2. Coach isolated parallel-wave snapshot run (``_run_isolated_tests``).
3. Deterministic Phase-4 runner (``specialist_invocations.py`` — delegates to
   CoachValidator with ``basetemp_context="phase4"``).
4. BDD runner subprocess (``bdd_runner._invoke_pytest_bdd``).

Operator-authored command strings (smoke gates, non-pytest shell commands)
must NOT gain the flag, and a pre-existing ``--basetemp`` wins.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.quality_gates.bdd_runner import _invoke_pytest_bdd
from guardkit.orchestrator.specialist_invocations import (
    _run_deterministic_phase_4,
)


def _make_validator(
    tmp_path: Path,
    test_cmd: str = "pytest tests/ -v",
    wave_size: int = 1,
    **kwargs,
) -> CoachValidator:
    validator = CoachValidator(
        worktree_path=tmp_path,
        task_id="TASK-AB-BASETEMP01",
        test_command=test_cmd,
        wave_size=wave_size,
        **kwargs,
    )
    validator._coach_test_execution = "subprocess"
    return validator


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _basetemp_value(cmd):
    """Return the value following ``--basetemp`` in an argv list."""
    idx = cmd.index("--basetemp")
    return cmd[idx + 1]


# ============================================================================
# 1. Coach standard subprocess path
# ============================================================================


class TestStandardSubprocessBasetemp:
    def test_injected_under_system_tmp_with_context(self, tmp_path):
        v = _make_validator(tmp_path, test_cmd="pytest tests/ -v --tb=short")
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert "--basetemp" in cmd
        basetemp = _basetemp_value(cmd)
        assert os.path.dirname(basetemp) == tempfile.gettempdir()
        assert "TASK-AB-BASETEMP01-coach-independent" in os.path.basename(basetemp)
        # Original argv contract untouched: pinned interpreter first, args kept.
        assert cmd[0] == sys.executable and cmd[1] == "-m" and cmd[2] == "pytest"
        assert "--tb=short" in cmd

    def test_basetemp_cleaned_up_after_run(self, tmp_path):
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(0, stdout="1 passed")) as mock_run:
            v.run_independent_tests()
        basetemp = _basetemp_value(mock_run.call_args.args[0])
        assert not os.path.exists(basetemp)

    def test_preexisting_basetemp_wins(self, tmp_path):
        """AC-003: an explicit --basetemp in the configured command is not
        overridden."""
        v = _make_validator(
            tmp_path, test_cmd="pytest tests/ --basetemp /custom/tmp"
        )
        with patch("subprocess.run", return_value=_proc(0, stdout="1 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert cmd.count("--basetemp") == 1
        assert _basetemp_value(cmd) == "/custom/tmp"

    def test_non_pytest_operator_command_untouched(self, tmp_path):
        """An operator-authored (non-pytest) command runs via shell=True as-is
        — no --basetemp mutation of operator policy strings."""
        v = _make_validator(tmp_path, test_cmd="python3 .guardkit/smoke/foo.py")
        with patch("subprocess.run", return_value=_proc(0, stdout="ok")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert cmd == "python3 .guardkit/smoke/foo.py"
        assert "--basetemp" not in cmd

    def test_verdict_semantics_unchanged(self, tmp_path):
        """AC-004: pure tmp-dir isolation — pass/fail classification intact."""
        v = _make_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stdout="1 failed")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False


# ============================================================================
# 2. Coach isolated parallel-wave snapshot path
# ============================================================================


class TestIsolatedRunBasetemp:
    def test_injected_with_isolated_context(self, tmp_path):
        v = _make_validator(tmp_path, wave_size=2)
        assert v.is_parallel is True
        with patch("subprocess.run", return_value=_proc(0, stdout="3 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert "--basetemp" in cmd
        basetemp = _basetemp_value(cmd)
        # The tempdir COPY isolates the CWD, but the basetemp must be its own
        # unique dir under the system temp dir — not the shared per-user
        # default, and not inside the snapshot copy.
        assert os.path.dirname(basetemp) == tempfile.gettempdir()
        assert "TASK-AB-BASETEMP01-coach-isolated" in os.path.basename(basetemp)
        assert not str(basetemp).startswith(str(mock_run.call_args.kwargs["cwd"]))

    def test_basetemp_cleaned_up_after_isolated_run(self, tmp_path):
        v = _make_validator(tmp_path, wave_size=2)
        with patch("subprocess.run", return_value=_proc(0, stdout="1 passed")) as mock_run:
            v.run_independent_tests()
        basetemp = _basetemp_value(mock_run.call_args.args[0])
        assert not os.path.exists(basetemp)

    def test_preexisting_basetemp_wins_isolated(self, tmp_path):
        v = _make_validator(
            tmp_path, test_cmd="pytest tests/ --basetemp=/custom/tmp", wave_size=2
        )
        with patch("subprocess.run", return_value=_proc(0, stdout="1 passed")) as mock_run:
            v.run_independent_tests()
        cmd = mock_run.call_args.args[0]
        assert "--basetemp=/custom/tmp" in cmd
        assert sum(
            1
            for tok in cmd
            if tok == "--basetemp" or tok.startswith("--basetemp=")
        ) == 1

    def test_concurrent_validators_get_distinct_basetemps(self, tmp_path):
        """AC-006c: two simulated concurrent invocations never share a
        basetemp."""
        seen = []

        def record(cmd, **kwargs):
            seen.append(_basetemp_value(cmd))
            return _proc(0, stdout="1 passed")

        v1 = _make_validator(tmp_path)
        v2 = _make_validator(tmp_path)
        with patch("subprocess.run", side_effect=record):
            v1.run_independent_tests()
            v2.run_independent_tests()
        assert len(seen) == 2
        assert seen[0] != seen[1]


# ============================================================================
# 3. Deterministic Phase-4 runner (specialist_invocations.py)
# ============================================================================


class TestPhase4BasetempContext:
    def test_phase4_threads_basetemp_context(self, tmp_path):
        """The PERTASKFG01 AC-004 subprocess labels its basetemp 'phase4' so a
        leaked dir is attributable to the Phase-4 runner, not the Coach."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.CoachValidator"
        ) as mock_cls:
            instance = mock_cls.return_value
            instance.run_independent_tests.return_value = SimpleNamespace(
                test_command="skipped",
                signal_absent=False,
                tests_passed=False,
                test_output_summary="",
                raw_output="",
            )
            result = _run_deterministic_phase_4(
                tmp_path,
                "TASK-AB-BASETEMP01",
                agent_invoker=SimpleNamespace(_venv_python=None),
                sdk_timeout=60,
                turn=1,
            )
        assert result is None  # "skipped" sentinel -> specialist fallback
        assert mock_cls.call_args.kwargs["basetemp_context"] == "phase4"

    def test_validator_context_override_reaches_prefix(self, tmp_path):
        """CoachValidator(basetemp_context='phase4') composes
        '<task_id>-phase4' for the run's basetemp prefix."""
        v = _make_validator(tmp_path, basetemp_context="phase4")
        assert v._basetemp_run_context("coach-independent") == (
            "TASK-AB-BASETEMP01-phase4"
        )
        with patch("subprocess.run", return_value=_proc(0, stdout="1 passed")) as mock_run:
            v.run_independent_tests()
        basetemp = _basetemp_value(mock_run.call_args.args[0])
        assert "TASK-AB-BASETEMP01-phase4" in os.path.basename(basetemp)

    def test_default_context_without_task_id(self, tmp_path):
        v = CoachValidator(worktree_path=tmp_path)
        v._coach_test_execution = "subprocess"
        assert v._basetemp_run_context("coach-independent") == "coach-independent"


# ============================================================================
# 4. BDD runner subprocess (_invoke_pytest_bdd)
# ============================================================================


class TestBddRunnerBasetemp:
    def test_injected_after_built_argv(self, tmp_path):
        feature = tmp_path / "features" / "x.feature"
        feature.parent.mkdir()
        feature.write_text("Feature: x\n")
        junit = tmp_path / ".guardkit" / "bdd" / "TASK-X_junit.xml"
        junit.parent.mkdir(parents=True)
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner.subprocess.run",
            return_value=_proc(0, stdout="1 passed"),
        ) as mock_run:
            _invoke_pytest_bdd(
                [feature],
                "@task:TASK-X",
                tmp_path,
                junit,
                timeout=10,
                task_id="TASK-X",
            )
        argv = mock_run.call_args.args[0]
        assert "--basetemp" in argv
        basetemp = _basetemp_value(argv)
        assert os.path.dirname(basetemp) == tempfile.gettempdir()
        assert "TASK-X-bdd" in os.path.basename(basetemp)
        assert not os.path.exists(basetemp)  # cleaned up after the run
        # --junitxml contract untouched: still points at the worktree path.
        assert f"--junitxml={junit}" in argv
        # Marker filter + feature file preserved.
        assert "-m" in argv and "task_TASK_X" in argv
        assert str(feature) in argv

    def test_no_task_id_uses_bare_bdd_context(self, tmp_path):
        feature = tmp_path / "x.feature"
        feature.write_text("Feature: x\n")
        junit = tmp_path / "junit.xml"
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner.subprocess.run",
            return_value=_proc(0),
        ) as mock_run:
            _invoke_pytest_bdd([feature], "@task:TASK-X", tmp_path, junit, timeout=10)
        argv = mock_run.call_args.args[0]
        assert os.path.basename(_basetemp_value(argv)).startswith(
            "guardkit-pytest-bdd-"
        )

    def test_timeout_sentinel_preserved_and_basetemp_cleaned(self, tmp_path):
        """The TASK-ABFIX-010 timeout sentinel (returncode -1, absent signal)
        is untouched, and the basetemp dir is cleaned even on timeout."""
        feature = tmp_path / "x.feature"
        feature.write_text("Feature: x\n")
        junit = tmp_path / "junit.xml"
        created = []

        real_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(*args, **kwargs):
            d = real_mkdtemp(*args, **kwargs)
            created.append(d)
            return d

        with patch(
            "guardkit.lib.pytest_argv.tempfile.mkdtemp",
            side_effect=tracking_mkdtemp,
        ), patch(
            "guardkit.orchestrator.quality_gates.bdd_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=10),
        ):
            invocation = _invoke_pytest_bdd(
                [feature], "@task:TASK-X", tmp_path, junit, timeout=10
            )
        assert invocation.returncode == -1  # _PYTEST_EXIT_TIMEOUT sentinel
        assert len(created) == 1
        assert not os.path.exists(created[0])
