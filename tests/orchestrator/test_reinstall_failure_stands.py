"""The declared install after a turn changes a file it serves.

Since the cull of 27 October 2026 a reinstall that fails, or cannot run
because its program is missing, is logged and the turn goes on: the
project's own tests then say what they say. Nothing here sends a turn back.
Since 1 November 2026 only a declared root install runs, and whether it is
due is the bootstrap's own record of the files it serves, not the builder's
report.

What each test pins:
- With no install declared nothing runs; a declared one runs when a file it
  serves changed, and not otherwise. -> ``TestTheReinstallRuns``
- A failed or raised reinstall never stops the turn.
  -> ``TestAFailedReinstallIsLogged``
- Only the program itself counts as a missing install tool.
  -> ``TestMissingInstallProgram``
- A feature whose task failed reports the count of failed tasks.
  -> ``TestTheFeatureLevel``
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.environment_bootstrap import _missing_program

TASK = "TASK-RFS-001"

RERUN = "guardkit.orchestrator.environment_bootstrap.rerun_declared_install_if_due"


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def _recorder(marker: Path, exit_code: int = 0) -> str:
    """A declared install (an argument list, no shell) that records a run."""
    script = (
        "import sys; "
        f"open({str(marker)!r}, 'a').write('install\\n'); "
        f"sys.exit({exit_code})"
    )
    return f"{sys.executable} -c {shlex.quote(script)}"


def _declare(root: Path, install: str) -> None:
    (root / ".guardkit").mkdir(exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"install": install, "test": "true"}}),
        encoding="utf-8",
    )


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "builder@example.invalid")
    _git(root, "config", "user.name", "builder")
    (root / "README.md").write_text("# demo\n")
    (root / "deps.txt").write_text("one\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")
    return root


def _bare_orchestrator() -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)


def _runs(marker: Path) -> int:
    return len(marker.read_text().splitlines()) if marker.exists() else 0


# ---------------------------------------------------------------------------
# The declared install runs when a file it serves changed
# ---------------------------------------------------------------------------


class TestTheReinstallRuns:
    def test_with_no_install_declared_nothing_runs(self, worktree: Path) -> None:
        (worktree / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        with patch("subprocess.run") as run:
            _bare_orchestrator()._maybe_rerun_declared_install(
                SimpleNamespace(path=str(worktree)), 1
            )
        run.assert_not_called()
        assert not (worktree / ".venv").exists()

    def test_a_changed_served_file_reruns_and_an_unchanged_one_does_not(
        self, worktree: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(worktree, _recorder(marker))
        orch = _bare_orchestrator()
        wt = SimpleNamespace(path=str(worktree))

        orch._maybe_rerun_declared_install(wt, 1)  # first time: due
        orch._maybe_rerun_declared_install(wt, 2)  # nothing changed
        (worktree / "deps.txt").write_text("one\ntwo\n")
        orch._maybe_rerun_declared_install(wt, 3)  # a served file changed

        assert _runs(marker) == 2


# ---------------------------------------------------------------------------
# A failed reinstall is logged and the turn goes on
# ---------------------------------------------------------------------------


class TestAFailedReinstallIsLogged:
    def test_a_failed_reinstall_is_logged_and_returns_nothing(
        self, worktree: Path, tmp_path: Path, caplog
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(worktree, _recorder(marker, exit_code=3))
        assert _bare_orchestrator()._maybe_rerun_declared_install(
            SimpleNamespace(path=str(worktree)), 1
        ) is None
        assert _runs(marker) == 1
        assert "failed" in caplog.text

    def test_a_raised_reinstall_returns_nothing(self, worktree: Path, caplog) -> None:
        with patch(RERUN, side_effect=RuntimeError("installer crashed")):
            assert _bare_orchestrator()._maybe_rerun_declared_install(
                SimpleNamespace(path=str(worktree)), 1
            ) is None
        assert "installer crashed" in caplog.text


# ---------------------------------------------------------------------------
# An install program that is not in the build environment at all
# ---------------------------------------------------------------------------


class TestMissingInstallProgram:
    def test_only_the_program_itself_counts_as_missing(self, tmp_path: Path) -> None:
        program = FileNotFoundError(2, "No such file or directory", "pnpm")
        folder = FileNotFoundError(2, "No such file or directory", str(tmp_path / "gone"))
        assert _missing_program(program, ["pnpm", "install"]) == "pnpm"
        assert _missing_program(folder, ["pnpm", "install"]) is None
        assert _missing_program(PermissionError(13, "denied", "pnpm"), ["pnpm"]) is None

    def test_a_missing_path_is_not_a_missing_tool(self, tmp_path: Path) -> None:
        """A project script is the project's: it is not a tool missing from
        the build environment, so it stays an ordinary failure."""
        script = FileNotFoundError(2, "No such file or directory", "./scripts/install.sh")
        assert _missing_program(script, ["./scripts/install.sh"]) is None


# ---------------------------------------------------------------------------
# The feature's final reason
# ---------------------------------------------------------------------------


def _feature_with_one_task():
    feature = MagicMock()
    feature.id = "FEAT-RFS1"
    feature.name = "Reinstall gap feature"
    feature.scenarios = {}
    task = MagicMock()
    task.id = TASK
    # The finaliser counts each task's own latest status (the wave ran it).
    task.status = "failed"
    feature.tasks = [task]
    return feature


def _failed_wave():
    from guardkit.orchestrator.feature_orchestrator import (
        TaskExecutionResult,
        WaveExecutionResult,
    )

    return WaveExecutionResult(
        wave_number=1,
        task_ids=[TASK],
        results=[
            TaskExecutionResult(
                task_id=TASK,
                success=False,
                total_turns=1,
                final_decision="error",
                error="the task failed",
            )
        ],
        all_succeeded=False,
    )


def _finalize(tmp_path: Path, waves, quiet: bool = True):
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
    from guardkit.worktrees import Worktree

    (tmp_path / "repo").mkdir(exist_ok=True)
    wt_path = tmp_path / "wt"
    wt_path.mkdir(exist_ok=True)
    orchestrator = FeatureOrchestrator(
        repo_root=tmp_path / "repo",
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=quiet,
    )
    worktree = Worktree(
        task_id="FEAT-RFS1",
        branch_name="autobuild/FEAT-RFS1",
        path=wt_path,
        base_branch="main",
    )
    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        return orchestrator._finalize_phase(_feature_with_one_task(), waves, worktree)


class TestTheFeatureLevel:
    def test_a_failed_task_is_counted_in_the_feature_error(
        self, tmp_path: Path, capsys
    ) -> None:
        result = _finalize(tmp_path, [_failed_wave()])
        assert result.success is False
        assert result.error == "1 task(s) failed"
        assert "GUARDKIT_STOPPED_BECAUSE" not in capsys.readouterr().out
