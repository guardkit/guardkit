"""TASK-AB-BASETEMP01 — per-run pytest ``--basetemp`` at every
orchestrator-constructed pytest call site.

Two concurrent autobuild loops raced on pytest's shared per-user
``/tmp/pytest-of-<user>`` basetemp (the FEAT-ABL-005 Coach died on that race
three turns straight). Every pytest argv the ORCHESTRATOR ITSELF constructs
must carry a unique ``--basetemp`` under the system temp dir:

4. BDD runner subprocess (``bdd_runner._invoke_pytest_bdd``).

(Items 1-3, the Coach's own pytest runs, went on 31 October 2026: the Coach
runs a project's declared command exactly as declared and adds no flags.)

Operator-authored command strings (smoke gates, non-pytest shell commands)
must NOT gain the flag, and a pre-existing ``--basetemp`` wins.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.quality_gates.bdd_runner import _invoke_pytest_bdd


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
