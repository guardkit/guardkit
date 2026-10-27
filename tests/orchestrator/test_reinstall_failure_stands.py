"""The dependency reinstall after a turn changes a dependency file.

Since the cull of 27 October 2026 a reinstall that fails, or cannot run
because a declared tool is missing, is logged and the turn goes on: the
project's own tests then say what they say. Nothing here sends a turn back.
What each test pins:

- The reinstall runs only when the turn changed a dependency file, with the
  changed files and the stacks they belong to. -> ``TestTheReinstallRuns``
- A failed or raised reinstall never stops the turn and leaves the
  interpreter alone; a successful one adopts the reinstalled interpreter.
  -> ``TestAFailedReinstallIsLogged``
- Only the program itself counts as a missing install tool.
  -> ``TestMissingInstallProgram``
- A feature whose task failed reports the count of failed tasks.
  -> ``TestTheFeatureLevel``
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.environment_bootstrap import (
    BootstrapFailureDetail,
    BootstrapResult,
    _missing_program,
)

TASK = "TASK-RFS-001"

PYPROJECT = """\
[project]
name = "workspace-root"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["member-pkg"]

[tool.uv.sources]
member-pkg = { workspace = true }

[tool.uv.workspace]
members = ["packages/*"]
"""

REFRESH = "guardkit.orchestrator.environment_bootstrap.refresh_environment_for_changes"


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "builder@example.invalid")
    _git(tmp_path, "config", "user.name", "builder")
    (tmp_path / "README.md").write_text("# demo\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    return tmp_path


def _bare_orchestrator() -> AutoBuildOrchestrator:
    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orch._venv_python = None
    return orch


def _player(files_modified=None, files_created=None) -> SimpleNamespace:
    return SimpleNamespace(
        report={
            "files_modified": list(files_modified or []),
            "files_created": list(files_created or []),
        }
    )


def _failed_result(path: Path) -> BootstrapResult:
    return BootstrapResult(
        success=False,
        skipped=False,
        stacks_detected=["python"],
        manifests_found=["pyproject.toml"],
        installs_attempted=1,
        installs_failed=1,
        error="1/1 install(s) failed",
        failure_details=[
            BootstrapFailureDetail(
                stack="python",
                manifest_path=str(path / "pyproject.toml"),
                stderr_excerpt="No matching distribution found for nope",
                essential=True,
            )
        ],
    )


def _ok_result() -> BootstrapResult:
    return BootstrapResult(
        success=True,
        skipped=False,
        stacks_detected=["python"],
        manifests_found=["pyproject.toml"],
    )


# ---------------------------------------------------------------------------
# The reinstall runs when a dependency file changed
# ---------------------------------------------------------------------------


class TestTheReinstallRuns:
    def test_a_turn_that_changes_no_dependency_file_reinstalls_nothing(
        self, worktree: Path
    ) -> None:
        orch = _bare_orchestrator()
        with patch(REFRESH) as refresh:
            assert orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["src/app.py"]),
                SimpleNamespace(path=str(worktree)),
                1,
            ) is None
        refresh.assert_not_called()

    def test_a_changed_dependency_file_is_reinstalled_with_its_stack(
        self, worktree: Path
    ) -> None:
        orch = _bare_orchestrator()
        with patch(REFRESH, return_value=_ok_result()) as refresh:
            orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml", "src/app.py"]),
                SimpleNamespace(path=str(worktree)),
                1,
            )
        refresh.assert_called_once()
        assert "pyproject.toml" in list(refresh.call_args.args[1])
        assert "python" in (refresh.call_args.kwargs.get("relevant_stacks") or [])


# ---------------------------------------------------------------------------
# A failed reinstall is logged and the turn goes on
# ---------------------------------------------------------------------------


class TestAFailedReinstallIsLogged:
    def test_a_failed_reinstall_returns_nothing_and_keeps_the_interpreter(
        self, worktree: Path, caplog
    ) -> None:
        orch = _bare_orchestrator()
        with patch(REFRESH, return_value=_failed_result(worktree)):
            assert orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml"]),
                SimpleNamespace(path=str(worktree)),
                1,
            ) is None
        assert orch._venv_python is None
        assert "No matching distribution found for nope" in caplog.text

    def test_a_raised_reinstall_returns_nothing(self, worktree: Path, caplog) -> None:
        orch = _bare_orchestrator()
        with patch(REFRESH, side_effect=RuntimeError("installer crashed")):
            assert orch._maybe_refresh_venv_for_manifest_change(
                _player(files_created=["pyproject.toml"]),
                SimpleNamespace(path=str(worktree)),
                1,
            ) is None
        assert "installer crashed" in caplog.text

    def test_a_successful_reinstall_adopts_its_interpreter(self, worktree: Path) -> None:
        orch = _bare_orchestrator()
        ok = _ok_result()
        ok.venv_python = str(worktree / ".venv" / "bin" / "python")
        with patch(REFRESH, return_value=ok):
            orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml"]),
                SimpleNamespace(path=str(worktree)),
                1,
            )
        assert orch._venv_python == ok.venv_python


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
        """The worktree's own interpreter can be rebuilt, and a project
        script is the project's: neither is a tool missing from the build
        environment, so both stay ordinary, blocking failures."""
        venv_python = str(tmp_path / ".venv" / "bin" / "python")
        missing = FileNotFoundError(2, "No such file or directory", venv_python)
        assert _missing_program(missing, [venv_python, "-m", "pip"]) is None
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
