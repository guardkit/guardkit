"""A dependency reinstall that could not run is never approved over (23 October 2026).

What a build showed: a project correctly declared ``[tool.uv.sources]`` in its
``pyproject.toml``, and ``uv`` was missing from the build environment. The
reinstall after turns 1 and 3 could not run, and that was only sent to the
builder as ordinary feedback. Turn 4 changed no dependency file, so nothing
re-checked, and the reviewer approved. The next wave's environment setup then
stopped hard on the same gap, hours later. The feedback had also told the
builder to remove the declaration, which would break the declared stack.

What each test below pins:

- A tool the project declares that is missing from the build environment ends
  the task on that turn as a configuration error, with a sentence naming the
  tool and the declaring file, that never tells anyone to remove the
  declaration, and the reviewer is not asked.
  -> ``TestMissingDeclaredTool``
- Any other failed reinstall stands until a later reinstall in the same task
  succeeds: a turn that changes no dependency file re-runs it, and the
  reviewer is not asked while it still fails.
  -> ``TestFailedReinstallStands``
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    _configuration_error_cause,
)
from guardkit.orchestrator.environment_bootstrap import (
    BootstrapFailureDetail,
    BootstrapResult,
    DeclaredToolMissingError,
    UvSourcesRequireUvError,
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
# A declared tool missing from the build environment
# ---------------------------------------------------------------------------


class TestMissingDeclaredTool:
    def test_the_uv_error_is_a_missing_declared_tool(self, worktree: Path) -> None:
        """The existing error carries the tool and the declaring file, and is
        decided on by its generic class, not a language name."""
        assert issubclass(UvSourcesRequireUvError, DeclaredToolMissingError)
        assert issubclass(UvSourcesRequireUvError, RuntimeError)
        bare = UvSourcesRequireUvError("message only")
        assert bare.tool is None and bare.declaring_file is None

    def test_reinstall_names_the_tool_and_file_and_keeps_the_declaration(
        self, worktree: Path
    ) -> None:
        orch = _bare_orchestrator()
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=False,
        ):
            feedback = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_created=["pyproject.toml"]),
                SimpleNamespace(path=str(worktree)),
                1,
            )
        assert feedback is not None
        assert orch._reinstall_environment_gap == feedback
        assert "`uv`" in feedback
        assert "pyproject.toml" in feedback
        assert str(worktree) not in feedback, "the file is named relative"
        assert "build environment" in feedback
        lowered = feedback.lower()
        assert "remov" not in lowered
        assert "delete" not in lowered

    def test_message_without_tool_or_file_still_reads(self, worktree: Path) -> None:
        orch = _bare_orchestrator()
        with patch(REFRESH, side_effect=DeclaredToolMissingError("gone")):
            feedback = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["package.json"]),
                SimpleNamespace(path=str(worktree)),
                2,
            )
        assert feedback == orch._reinstall_environment_gap
        assert "missing a tool, which package.json declares" in feedback

    def test_the_turn_ends_as_a_configuration_error_without_the_reviewer(
        self, worktree: Path
    ) -> None:
        invoker = Mock()
        invoker.invoke_player = AsyncMock(
            return_value=AgentInvocationResult(
                task_id=TASK, turn=1, agent_type="player", success=True,
                report={"task_id": TASK, "files_modified": [],
                        "files_created": ["pyproject.toml"], "tests_written": []},
                duration_seconds=60.0,
            )
        )
        invoker.invoke_coach = AsyncMock()
        invoker._get_implementation_mode.return_value = "direct"
        manager = Mock()
        manager.worktrees_dir = worktree
        orch = AutoBuildOrchestrator(
            repo_root=worktree,
            max_turns=5,
            worktree_manager=manager,
            agent_invoker=invoker,
            progress_display=MagicMock(),
            enable_pre_loop=False,
            enable_checkpoints=False,
        )
        wt = SimpleNamespace(path=worktree, branch_name="main")
        with patch.object(orch, "_attempt_state_recovery", return_value=None), \
                patch.object(orch, "_invoke_coach_safely") as coach, \
                patch(
                    "guardkit.orchestrator.environment_bootstrap._uv_on_path",
                    return_value=False,
                ):
            record = orch._execute_turn(
                turn=1, task_id=TASK, requirements="Set up the workspace",
                worktree=wt, previous_feedback=None,
            )
        coach.assert_not_called()
        assert record.is_configuration_error is True
        assert record.coach_result is None
        cause, is_task_type = _configuration_error_cause(record)
        assert is_task_type is False
        assert "`uv`" in cause and "pyproject.toml" in cause
        assert "remov" not in cause.lower()


# ---------------------------------------------------------------------------
# Any other failed reinstall stands until a later one succeeds
# ---------------------------------------------------------------------------


class TestFailedReinstallStands:
    def test_blocks_until_a_later_reinstall_succeeds(self, worktree: Path) -> None:
        orch = _bare_orchestrator()
        wt = SimpleNamespace(path=str(worktree))

        # Turn 1 changes the dependency file and the reinstall fails.
        with patch(REFRESH, return_value=_failed_result(worktree)) as refresh:
            first = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml"]), wt, 1
            )
        assert first is not None and "reinstall failed" in first.lower()
        assert orch._reinstall_environment_gap is None
        refresh.assert_called_once()

        # Turn 2 changes only source: the reinstall is re-run, still fails,
        # and the turn is still refused.
        with patch(REFRESH, return_value=_failed_result(worktree)) as refresh:
            second = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["src/app.py"]), wt, 2
            )
        refresh.assert_called_once()
        assert "pyproject.toml" in list(refresh.call_args.args[1])
        assert second is not None
        assert "has not succeeded since turn 1" in second
        assert "cannot be approved" in second
        # Says which turn changed the files, not "this turn".
        assert "after turn 1 modified pyproject.toml" in second
        assert "this turn" not in second

        # Turn 3 changes only source and the re-run reinstall succeeds.
        with patch(REFRESH, return_value=_ok_result()) as refresh:
            third = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["src/app.py"]), wt, 3
            )
        refresh.assert_called_once()
        assert third is None

        # Turn 4: cleared, so nothing is re-run — today's behaviour.
        with patch(REFRESH) as refresh:
            fourth = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["src/app.py"]), wt, 4
            )
        refresh.assert_not_called()
        assert fourth is None

    def test_a_raised_failure_also_stands(self, worktree: Path) -> None:
        orch = _bare_orchestrator()
        wt = SimpleNamespace(path=str(worktree))
        with patch(REFRESH, side_effect=RuntimeError("installer crashed")):
            assert orch._maybe_refresh_venv_for_manifest_change(
                _player(files_created=["pyproject.toml"]), wt, 1
            )
        with patch(REFRESH, side_effect=RuntimeError("installer crashed")) as refresh:
            again = orch._maybe_refresh_venv_for_manifest_change(_player(), wt, 2)
        refresh.assert_called_once()
        assert "installer crashed" in again
        assert "has not succeeded since turn 1" in again

    def test_a_different_dependency_file_cannot_clear_it(self, worktree: Path) -> None:
        """Turn 1 fails on pyproject.toml; turn 2 changes only package.json.
        The re-run must still include pyproject.toml, so the failure stands
        while pyproject.toml does not install."""
        orch = _bare_orchestrator()
        wt = SimpleNamespace(path=str(worktree))
        (worktree / "package.json").write_text("{}")

        def refresh(root, changed, relevant_stacks=None):
            return (
                _failed_result(worktree)
                if "pyproject.toml" in list(changed)
                else _ok_result()
            )

        with patch(REFRESH, side_effect=refresh):
            assert orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml"]), wt, 1
            )
        with patch(REFRESH, side_effect=refresh) as mock_refresh:
            second = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["package.json"]), wt, 2
            )
        passed = list(mock_refresh.call_args.args[1])
        assert "pyproject.toml" in passed and "package.json" in passed
        assert "python" in (mock_refresh.call_args.kwargs.get("relevant_stacks") or [])
        assert second is not None
        assert "after turns 1 and 2 modified" in second
        assert orch._standing_reinstall_failure is not None
        assert orch._standing_reinstall_failure[0] == 1


# ---------------------------------------------------------------------------
# An install program that is not in the build environment at all
# ---------------------------------------------------------------------------


class TestMissingInstallProgram:
    def test_a_lockfile_naming_a_missing_installer_ends_the_task(
        self, worktree: Path, tmp_path_factory, monkeypatch
    ) -> None:
        """Through the real bootstrap: the lock file names an installer that
        is not on PATH. The task gets the environment-gap sentence, never
        advice to fix the declaration."""
        (worktree / "pyproject.toml").unlink()
        (worktree / "package.json").write_text('{"name":"demo","version":"0.0.1"}')
        (worktree / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
        empty_path = tmp_path_factory.mktemp("empty-path")
        monkeypatch.setenv("PATH", str(empty_path))

        orch = _bare_orchestrator()
        msg = orch._maybe_refresh_venv_for_manifest_change(
            _player(files_modified=["package.json"]),
            SimpleNamespace(path=str(worktree)),
            1,
        )
        assert msg is not None
        assert msg == orch._reinstall_environment_gap
        assert "`pnpm`" in msg
        assert "pnpm-lock.yaml declares" in msg
        assert "build environment" in msg
        assert "Fix the dependency declaration" not in msg
        assert "remov" not in msg.lower()

    def test_a_partly_missing_or_replayed_failure_stays_blocking(
        self, worktree: Path
    ) -> None:
        """Only when every essential failure is a missing program does the
        task end; a failure replayed from the saved record has no program
        name and stays an ordinary, blocking failure."""
        failed = _failed_result(worktree)
        failed.failure_details.append(
            BootstrapFailureDetail(
                stack="node",
                manifest_path=str(worktree / "pnpm-lock.yaml"),
                stderr_excerpt="[Errno 2] No such file or directory: 'pnpm'",
                essential=True,
                missing_tool="pnpm",
            )
        )
        orch = _bare_orchestrator()
        with patch(REFRESH, return_value=failed):
            msg = orch._maybe_refresh_venv_for_manifest_change(
                _player(files_modified=["pyproject.toml"]),
                SimpleNamespace(path=str(worktree)),
                1,
            )
        assert msg is not None and orch._reinstall_environment_gap is None
        assert orch._standing_reinstall_failure is not None

    def test_only_the_program_itself_counts_as_missing(self, tmp_path: Path) -> None:
        program = FileNotFoundError(2, "No such file or directory", "pnpm")
        folder = FileNotFoundError(2, "No such file or directory", str(tmp_path / "gone"))
        assert _missing_program(program, ["pnpm", "install"]) == "pnpm"
        assert _missing_program(folder, ["pnpm", "install"]) is None
        assert _missing_program(PermissionError(13, "denied", "pnpm"), ["pnpm"]) is None
