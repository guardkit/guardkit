"""A task can set up the project's coverage command through a build.

20 October 2026. The task-start coverage check (19 October) stops a task that
needs measured coverage when the project declares no coverage command. It
also stopped the task whose own work was to declare that command, and the
pinned declaration every task is judged by is cut from the canonical
repository, so nothing an earlier task of the same build declared was ever
seen. A project could never get coverage set up through the factory.

Checked here:

* a task that says it will change ``.guardkit/config.yaml`` is not stopped;
  after its turn the coverage command it wrote is pinned and the Coach
  measures coverage with it, on that turn, through the real loop;
* a task that says so but declares no coverage command stops after its turn
  with the same plain reason, worded for a stop after the turn;
* a task that does not touch the file still stops before any work;
* a coverage command an earlier task of the same build declared in the
  worktree reaches the next task's pin, so that task is not stopped;
* only the coverage command is ever taken from the worktree, a pinned one is
  never replaced, and the component rule is kept.

Invented projects only; no model is called.
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    UNDECLARED_COVERAGE_CAUSE,
    AutoBuildOrchestrator,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import (
    ToolchainDeclaration,
    add_coverage_to_pin,
    declares_config_file,
    does_nothing_command,
    load_coverage_only_pin,
    load_toolchain_snapshot,
    toolchain_snapshot_paths,
)
from guardkit.worktrees.manager import Worktree

pytestmark = pytest.mark.coverage_declaration_check

TASK = "TASK-SETUP-002"

NO_COVERAGE = 'toolchain:\n  test: "make test"\n  lint: "make lint"\n'
COVERAGE_COMMAND = "touch coverage-ran.marker && exit 0"
WITH_COVERAGE = (
    'toolchain:\n  test: "make test"\n  lint: "make lint"\n'
    f'  coverage: "{COVERAGE_COMMAND}"\n  coverage_timeout: 120\n'
)

# Both declare a source file, so coverage is still needed. A task declaring
# only configuration files is covered by TestAConfigurationOnlySetupTask.
DECLARES_CONFIG = (
    "## Files to Create\n- _none_\n\n"
    "## Files to Modify\n- `.guardkit/config.yaml` — declare the coverage command\n"
    "- `src/greeting.c`\n"
)
DECLARES_OTHER = "## Files to Create\n- `src/greeting.c`\n\n## Files to Modify\n- _none_\n"
DECLARES_ONLY_CONFIG = (
    "## Files to Create\n- _none_\n\n"
    "## Files to Modify\n- `.guardkit/config.yaml` — declare the coverage command\n"
    "- `deploy/compose.yaml`\n"
)


def _decl(**raw: Any) -> ToolchainDeclaration:
    return ToolchainDeclaration.model_validate(raw)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Coverage Test",
         "-c", "user.email=coverage@example.invalid", *args],
        check=True, capture_output=True, text=True,
    )


def _project(
    root: Path,
    *,
    body: str,
    task_type: Optional[str] = "feature",
    config: str = NO_COVERAGE,
    frontmatter_extra: Optional[List[str]] = None,
) -> None:
    """An invented project with one task, committed on a work branch."""
    (root / ".guardkit").mkdir(parents=True, exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(config, encoding="utf-8")
    front = [f"id: {TASK}", "title: Set up coverage measurement"]
    if task_type is not None:
        front.append(f"task_type: {task_type}")
    front.extend(frontmatter_extra or [])
    tasks = root / "tasks" / "backlog"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / f"{TASK}-coverage.md").write_text(
        "---\n" + "\n".join(front) + "\n---\n\n# Coverage\n\n" + body,
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(".guardkit/autobuild-private/\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")


def _shared_worktree(root: Path, where: Path) -> Path:
    """A real git worktree beside the canonical tree, as a feature build has."""
    _git(root, "worktree", "add", "-q", "-b", "autobuild/FEAT-SETUP", str(where))
    return where


def _earlier_wave_commits(worktree: Path, config: str) -> None:
    """What an earlier task of the same build left in the shared worktree."""
    (worktree / ".guardkit" / "config.yaml").write_text(config, encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "[guardkit-checkpoint] Turn 1 complete")


def _orchestrator(
    tmp_path: Path, root: Path, worktree_path: Path, *, feature: bool = False
):
    worktree = MagicMock(spec=Worktree)
    worktree.task_id = TASK
    worktree.path = worktree_path
    worktree.branch_name = "autobuild/FEAT-SETUP"
    worktree.base_branch = "main"
    manager = MagicMock()
    manager.create.return_value = worktree
    manager.worktrees_dir = tmp_path / "worktrees"
    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(side_effect=AssertionError("no real Player"))
    invoker.invoke_coach = AsyncMock(side_effect=AssertionError("no real Coach"))
    orch = AutoBuildOrchestrator(
        repo_root=root,
        max_turns=3,
        worktree_manager=manager,
        agent_invoker=invoker,
        progress_display=MagicMock(),
        pre_loop_gates=MagicMock(),
        enable_pre_loop=False,
        enable_checkpoints=False,
        enable_context=False,
        # A feature's tasks run in the feature's shared worktree, handed in.
        existing_worktree=worktree if feature else None,
    )
    return orch


def _player_result(turn: int, task_id: str = TASK) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id, turn=turn, agent_type="player", success=True,
        report={"task_id": task_id, "turn": turn, "files_modified": [".guardkit/config.yaml"]},
        duration_seconds=1.0, error=None,
    )


def _approve(turn: int, task_id: str = TASK) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id, turn=turn, agent_type="coach", success=True,
        report={
            "task_id": task_id, "turn": turn, "decision": "approve", "issues": [],
            "rationale": "coverage measured", "is_configuration_error": False,
        },
        duration_seconds=1.0, error=None,
    )


class _Turns:
    """The Player stand-in and the Coach's own coverage measurement.

    The Player edits the worktree's config (or not). The Coach stand-in
    builds the real ``CoachValidator`` the primary Coach path builds, from
    the pinned declaration, and runs the project's declared coverage
    command with it: that is what decides ``coverage_met`` on the real path.
    """

    def __init__(self, worktree: Path, new_config: Optional[str]) -> None:
        self.worktree = worktree
        self.new_config = new_config
        self.player_turns = 0
        self.coach_receipts: List[Optional[Dict[str, Any]]] = []
        # What each Coach saw as the project's declared test command, and
        # whether it held a declaration at all.
        self.coach_test_commands: List[Optional[str]] = []
        self.coach_had_declaration: List[bool] = []

    def player(self, *args: Any, **kwargs: Any) -> AgentInvocationResult:
        self.player_turns += 1
        if self.new_config is not None:
            (self.worktree / ".guardkit" / "config.yaml").write_text(
                self.new_config, encoding="utf-8"
            )
        return _player_result(
            kwargs.get("turn", self.player_turns), kwargs.get("task_id", TASK)
        )

    def coach(self, *args: Any, **kwargs: Any) -> AgentInvocationResult:
        validator = CoachValidator(str(self.worktree), task_id=kwargs["task_id"])
        self.coach_receipts.append(validator.run_declared_coverage())
        self.coach_test_commands.append(validator._declared_test_command())
        self.coach_had_declaration.append(validator._toolchain is not None)
        return _approve(kwargs["turn"], kwargs["task_id"])


def _run_real_loop(orch: AutoBuildOrchestrator, turns: _Turns, task_id: str = TASK):
    with patch.object(
        AutoBuildOrchestrator, "_invoke_player_safely",
        autospec=True, side_effect=lambda self, *a, **k: turns.player(*a, **k),
    ), patch.object(
        AutoBuildOrchestrator, "_invoke_coach_primary",
        autospec=True, side_effect=lambda self, *a, **k: turns.coach(*a, **k),
    ), patch.object(
        AutoBuildOrchestrator, "_resolve_tests_required", return_value=False,
    ), patch.object(
        AutoBuildOrchestrator, "_build_player_summary", return_value="Player ok",
    ), patch(
        # The orchestrator's own Phase-4 test specialist is not the subject
        # here (in a project with no declared test command it would start a
        # model call); it reports "skipped", so Phase 5 does not run either.
        "guardkit.orchestrator.specialist_invocations.invoke_test_orchestrator",
        new=AsyncMock(return_value=SimpleNamespace(status="skipped")),
    ):
        return orch.orchestrate(
            task_id=task_id, requirements="Declare the coverage command",
            acceptance_criteria=["AC-001: coverage is declared"],
        )


# ---------------------------------------------------------------------------
# Through orchestrate and the real loop
# ---------------------------------------------------------------------------


class TestATaskThatDeclaresTheCommand:
    def test_wave_two_task_declaring_it_is_measured_with_the_new_command(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        # Wave 1 changed something else in the shared worktree.
        (worktree / "Makefile").write_text("coverage:\n\ttrue\n")
        _git(worktree, "add", "-A")
        _git(worktree, "commit", "-q", "-m", "[guardkit-checkpoint] wave 1")

        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, WITH_COVERAGE)
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1  # not stopped before work
        assert result.final_decision == "approved", result.error
        assert result.success is True
        # The Coach of that very turn measured coverage with the new command.
        assert len(turns.coach_receipts) == 1
        receipt = turns.coach_receipts[0]
        assert receipt is not None
        assert receipt["command"] == COVERAGE_COMMAND
        assert receipt["exit_code"] == 0
        assert receipt["coverage_met"] is True
        assert (worktree / "coverage-ran.marker").exists()
        # Only coverage came from the worktree; it is now pinned.
        pinned = load_toolchain_snapshot(TASK, worktree)
        assert pinned.coverage == COVERAGE_COMMAND
        assert pinned.coverage_timeout == 120
        assert pinned.test == "make test"
        assert orch._coverage_declaration_refusal is None
        assert orch._coverage_due_from_task is None

    def test_declaring_the_file_but_no_command_stops_after_the_turn(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        # The turn changes the file, but declares no coverage command.
        turns = _Turns(worktree, NO_COVERAGE + '  build: "make"\n')
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1  # one turn, then stopped
        assert turns.coach_receipts == []  # the Coach never judged it
        assert result.final_decision == "configuration_error"
        assert result.success is False
        assert result.total_turns == 1
        assert "declares no coverage command" in result.error
        assert "after that turn the file still declares none" in result.error
        assert "stopped before any work was done" not in result.error
        assert result.error.startswith("Stopped after the task's turn")
        assert "Fix the task_type" not in result.error
        coach = result.turn_history[0].coach_result.report
        assert coach["is_configuration_error"] is True
        assert coach["issues"][-1]["category"] == UNDECLARED_COVERAGE_CAUSE
        summary = orch._build_summary_details(result.turn_history, "configuration_error")
        assert summary.startswith("Stopped after the task's turn")
        assert "task_type" not in summary
        assert load_toolchain_snapshot(TASK, worktree).coverage is None

    def test_a_task_not_touching_the_file_still_stops_before_any_work(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, WITH_COVERAGE)
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 0
        assert result.final_decision == "configuration_error"
        assert result.total_turns == 0
        assert "it was stopped before any work was done" in result.error
        assert orch._coverage_due_from_task is None

    def test_files_listed_in_frontmatter_count_too(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(
            root, body="No file sections here.\n",
            frontmatter_extra=["files_to_modify:", "  - ./.guardkit/config.yaml"],
        )
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, WITH_COVERAGE)
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        assert turns.coach_receipts[0]["command"] == COVERAGE_COMMAND



class TestAConfigurationOnlySetupTask:
    """23 October 2026: a task that declares only configuration files, one of
    them .guardkit/config.yaml, still takes the setup path, so a coverage
    command it writes is pinned and measured on its own turn; but declaring
    none does not stop it, because it has no source code to measure."""

    def test_the_command_it_writes_is_measured_on_its_own_turn(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_ONLY_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, WITH_COVERAGE)
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        assert turns.coach_receipts[0]["command"] == COVERAGE_COMMAND
        assert load_toolchain_snapshot(TASK, worktree).coverage == COVERAGE_COMMAND

    def test_declaring_no_command_does_not_stop_it(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_ONLY_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, NO_COVERAGE + '  build: "make"\n')
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        assert turns.coach_receipts == [None]  # nothing declared, nothing run
        assert orch._coverage_declaration_refusal is None
        assert orch._coverage_due_from_task is None

    def test_a_command_that_does_nothing_still_stops_it(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_ONLY_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, NO_COVERAGE + '  coverage: "true"\n')
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 1
        assert result.final_decision == "configuration_error"
        assert "The coverage command `true`" in result.error
        assert result.error.startswith("Stopped after the task's turn")


NO_TOOLCHAIN = "memory:\n  project: demo\n"


class TestAProjectWithNoToolchainBlock:
    """Review round 1: the first declaration can be made through a build too.
    Only the coverage command is ever taken from the worktree; the test
    command keeps its no-declaration behaviour."""

    def test_first_time_setup_is_measured_on_the_same_turn(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG, config=NO_TOOLCHAIN)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        # The turn writes a whole toolchain block, test command included.
        turns = _Turns(worktree, NO_TOOLCHAIN + WITH_COVERAGE)
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        receipt = turns.coach_receipts[0]
        assert receipt["command"] == COVERAGE_COMMAND
        assert receipt["coverage_met"] is True
        assert (worktree / "coverage-ran.marker").exists()
        # The test command the turn wrote was NOT taken: no declaration is
        # pinned, so the Coach holds none and declares no test command.
        assert turns.coach_had_declaration == [False]
        assert turns.coach_test_commands == [None]
        assert load_toolchain_snapshot(TASK, worktree) is None
        assert load_coverage_only_pin(TASK, worktree) == (COVERAGE_COMMAND, 120)

    def test_still_absent_after_the_turn_stops_there(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG, config=NO_TOOLCHAIN)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, NO_TOOLCHAIN + 'toolchain:\n  test: "make test"\n')
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1
        assert turns.coach_receipts == []
        assert result.final_decision == "configuration_error"
        assert result.error.startswith("Stopped after the task's turn")
        assert "after that turn the file still declares none" in result.error
        assert load_coverage_only_pin(TASK, worktree) is None

    def test_an_earlier_wave_adding_the_first_declaration_is_seen(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER, config=NO_TOOLCHAIN)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(worktree, NO_TOOLCHAIN + WITH_COVERAGE)
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, None)
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        assert turns.coach_receipts[0]["command"] == COVERAGE_COMMAND
        assert turns.coach_had_declaration == [False]
        assert turns.coach_test_commands == [None]

    def test_without_the_file_it_still_stops_before_work(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER, config=NO_TOOLCHAIN)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, NO_TOOLCHAIN + WITH_COVERAGE)
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 0
        assert "stopped before any work was done" in result.error

    def test_a_component_task_with_nothing_pinned_is_not_offered_a_turn(
        self, tmp_path: Path
    ) -> None:
        """With nothing pinned the Coach cannot resolve any component, so the
        turn is not offered (a real task naming an undeclared component
        already fails at task load)."""
        orch = _orchestrator(tmp_path, tmp_path, tmp_path)
        worktree = MagicMock(spec=Worktree)
        worktree.path = tmp_path
        paths = [".guardkit/config.yaml"]
        assert orch._task_declares_coverage_setup(TASK, worktree, paths) is True
        assert orch._task_declares_coverage_setup(
            TASK, worktree, paths, component="web"
        ) is False


class TestEarlierWorkInTheSameBuild:
    def test_a_command_an_earlier_task_declared_reaches_the_next_task(
        self, tmp_path: Path
    ) -> None:
        """Wave 1 declared the command; wave 2's feature task (which does not
        touch the file) is not stopped and its Coach measures with it."""
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(worktree, WITH_COVERAGE)
        # The canonical tree still declares none.
        assert "coverage" not in (root / ".guardkit" / "config.yaml").read_text()

        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, None)
        result = _run_real_loop(orch, turns)

        assert turns.player_turns == 1
        assert result.final_decision == "approved", result.error
        assert turns.coach_receipts[0]["command"] == COVERAGE_COMMAND
        assert turns.coach_receipts[0]["coverage_met"] is True

    def test_other_commands_still_come_from_the_canonical_tree(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(
            worktree,
            'toolchain:\n  test: "true"\n  lint: "true"\n'
            f'  coverage: "{COVERAGE_COMMAND}"\n',
        )
        orch = _orchestrator(tmp_path, root, worktree)
        _run_real_loop(orch, _Turns(worktree, None))
        pinned = load_toolchain_snapshot(TASK, worktree)
        assert pinned.test == "make test"
        assert pinned.lint == "make lint"
        assert pinned.coverage == COVERAGE_COMMAND

    def test_a_pinned_command_is_never_replaced(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(
            root, body=DECLARES_CONFIG,
            config='toolchain:\n  test: "make test"\n  coverage: "make cov"\n',
        )
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, WITH_COVERAGE)
        _run_real_loop(orch, turns)
        assert turns.coach_receipts[0]["command"] == "make cov"
        assert load_toolchain_snapshot(TASK, worktree).coverage == "make cov"


# ---------------------------------------------------------------------------
# The pieces
# ---------------------------------------------------------------------------


class TestDeclaresConfigFile:
    @pytest.mark.parametrize(
        "paths",
        [
            [".guardkit/config.yaml"],
            ["./.guardkit/config.yaml"],
            ["src/a.py", "`.guardkit/config.yaml`"],
            [".guardkit\\config.yaml"],
        ],
    )
    def test_named(self, paths) -> None:
        assert declares_config_file(paths) is True

    @pytest.mark.parametrize(
        "paths",
        [
            [],
            [".guardkit/config.yml"],
            ["app/.guardkit/config.yaml"],
            [".guardkit/features/FEAT-1.yaml"],
            [None, 3, ""],
        ],
    )
    def test_not_named(self, paths) -> None:
        assert declares_config_file(paths) is False

    def test_the_task_document_sections_are_read(self) -> None:
        paths = AutoBuildOrchestrator._task_declared_paths(
            "---\nid: X\n---\n\n" + DECLARES_CONFIG, {}
        )
        assert ".guardkit/config.yaml" in paths
        assert "src/greeting.c" in paths


def _pin(task_id: str, worktree: Path, decl: ToolchainDeclaration) -> None:
    paths = toolchain_snapshot_paths(task_id, worktree)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["file"].write_text(json.dumps(decl.model_dump(mode="json")))


class TestAddCoverageToPin:
    def test_adds_only_coverage_and_its_timeout(self, tmp_path: Path) -> None:
        _pin(TASK, tmp_path, _decl(test="make test", lint="make lint"))
        source = _decl(test="true", lint="true", coverage="make cov", coverage_timeout=90)
        assert add_coverage_to_pin(TASK, tmp_path, source) == "make cov"
        pinned = load_toolchain_snapshot(TASK, tmp_path)
        assert (pinned.test, pinned.lint) == ("make test", "make lint")
        assert (pinned.coverage, pinned.coverage_timeout) == ("make cov", 90)

    def test_never_replaces(self, tmp_path: Path) -> None:
        _pin(TASK, tmp_path, _decl(test="make test", coverage="make cov"))
        assert add_coverage_to_pin(TASK, tmp_path, _decl(coverage="true")) is None
        assert load_toolchain_snapshot(TASK, tmp_path).coverage == "make cov"

    def test_nothing_pinned_keeps_coverage_alone(self, tmp_path: Path) -> None:
        source = _decl(test="true", coverage="make cov", coverage_timeout=45)
        assert add_coverage_to_pin(TASK, tmp_path, source, "web") is None
        assert add_coverage_to_pin(TASK, tmp_path, source) == "make cov"
        assert load_toolchain_snapshot(TASK, tmp_path) is None
        assert load_coverage_only_pin(TASK, tmp_path) == ("make cov", 45)
        # Never replaced.
        assert add_coverage_to_pin(TASK, tmp_path, _decl(coverage="true")) is None
        assert load_coverage_only_pin(TASK, tmp_path) == ("make cov", 45)
        validator = CoachValidator(str(tmp_path), task_id=TASK)
        assert validator._toolchain is None
        assert validator._declared_test_command() is None
        assert validator._declared_coverage_command() == "make cov"
        assert validator._declared_coverage_timeout() == 45
        # A component task never borrows it.
        assert CoachValidator(
            str(tmp_path), task_id=TASK, component="web"
        )._declared_coverage_command() is None

    def test_nothing_without_a_source_command(self, tmp_path: Path) -> None:
        _pin(TASK, tmp_path, _decl(test="make test"))
        assert add_coverage_to_pin(TASK, tmp_path, None) is None
        assert add_coverage_to_pin(TASK, tmp_path, _decl(test="t")) is None
        assert load_toolchain_snapshot(TASK, tmp_path).coverage is None

    def test_component_rule(self, tmp_path: Path) -> None:
        _pin(TASK, tmp_path, _decl(
            test="make test",
            components={"web": {"cwd": "web", "test": "npm test"}},
        ))
        # The root's coverage is never a component's.
        assert add_coverage_to_pin(TASK, tmp_path, _decl(coverage="root cov"), "web") is None
        source = _decl(components={
            "web": {"cwd": "web", "test": "x", "coverage": "npm run cov",
                    "coverage_timeout": 75},
        })
        assert add_coverage_to_pin(TASK, tmp_path, source, "web") == "npm run cov"
        pinned = load_toolchain_snapshot(TASK, tmp_path)
        web = pinned.component("web")
        assert (web.test, web.coverage, web.coverage_timeout) == ("npm test", "npm run cov", 75)
        assert pinned.coverage is None
        # A component the pin does not define is not added.
        assert add_coverage_to_pin(
            TASK, tmp_path,
            _decl(components={"api": {"cwd": "api", "coverage": "go cov"}}), "api",
        ) is None


# ---------------------------------------------------------------------------
# Coach review 1
# ---------------------------------------------------------------------------


def _add_task(root: Path, task_id: str, body: str, task_type: str = "feature") -> None:
    """Another task of the same build, in the canonical tree's task folder."""
    (root / "tasks" / "backlog" / f"{task_id}-more.md").write_text(
        f"---\nid: {task_id}\ntitle: More work\ntask_type: {task_type}\n---\n\n"
        f"# More\n\n{body}",
        encoding="utf-8",
    )


class TestALaterTaskCannotWeakenCoverage:
    """Once a task of the build has pinned a coverage command, every later
    task reuses it and never re-reads the worktree file."""

    def test_a_rewrite_to_true_does_not_reach_later_tasks(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG)
        _add_task(root, "TASK-SETUP-005", DECLARES_OTHER)
        _add_task(root, "TASK-SETUP-006", DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")

        # Task 3 declares the command on its own turn.
        first = _Turns(worktree, WITH_COVERAGE)
        assert _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), first
        ).final_decision == "approved"
        assert first.coach_receipts[0]["command"] == COVERAGE_COMMAND

        # Task 4's Player rewrites the file to a command that always passes.
        weakened = (
            'toolchain:\n  test: "true"\n  lint: "make lint"\n  coverage: "true"\n'
        )
        fourth = _Turns(worktree, weakened)
        assert _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), fourth, "TASK-SETUP-005"
        ).final_decision == "approved"
        # Task 4 itself was measured with the build's pinned command.
        assert fourth.coach_receipts[0]["command"] == COVERAGE_COMMAND

        # Task 5 is measured with the first command, not "true".
        fifth = _Turns(worktree, None)
        result = _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), fifth, "TASK-SETUP-006"
        )
        assert result.final_decision == "approved", result.error
        assert fifth.coach_receipts[0]["command"] == COVERAGE_COMMAND
        assert load_toolchain_snapshot("TASK-SETUP-006", worktree).coverage == COVERAGE_COMMAND
        assert load_toolchain_snapshot("TASK-SETUP-006", worktree).test == "make test"

    def test_an_earlier_waves_command_is_recorded_on_first_read(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        _add_task(root, "TASK-SETUP-005", DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(worktree, WITH_COVERAGE)
        assert _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), _Turns(worktree, None)
        ).final_decision == "approved"
        _earlier_wave_commits(worktree, NO_COVERAGE + '  coverage: "exit 0"\n')
        later = _Turns(worktree, None)
        assert _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), later, "TASK-SETUP-005"
        ).final_decision == "approved"
        assert later.coach_receipts[0]["command"] == COVERAGE_COMMAND

    def test_a_canonically_pinned_command_means_the_worktree_is_not_read(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """With the canonical repository's coverage pinned, the worktree's
        value (even a do-nothing one) is neither judged nor recorded."""
        worktree = tmp_path / "shared"
        (worktree / ".guardkit").mkdir(parents=True)
        (worktree / ".guardkit" / "config.yaml").write_text(
            'toolchain:\n  test: "make test"\n  coverage: "true"\n'
        )
        _pin(TASK, worktree, _decl(test="make test", coverage="make cov"))
        orch = _orchestrator(tmp_path, worktree, worktree)
        handle = MagicMock(spec=Worktree)
        handle.path = worktree
        with caplog.at_level("INFO"):
            assert orch._carry_coverage_from_worktree(
                TASK, handle, component=None, when="test"
            ) == (None, None)
        assert "does nothing" not in caplog.text
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) is None
        assert load_toolchain_snapshot(TASK, worktree).coverage == "make cov"

    def test_each_component_has_its_own_entry(self, tmp_path: Path) -> None:
        """Coach review 2 (P12): a component's command is recorded under that
        component, a later task of the same component reuses it, and a root
        task never sees it."""
        from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

        root = tmp_path / "proj"
        _project(
            root, body=DECLARES_OTHER,
            config=COMPONENTS_CANONICAL,
        )
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(
            worktree,
            _components_with_coverage("make web-cov", "make api-cov").replace(
                '  test: "make test"\n', '  test: "make test"\n  coverage: "make root-cov"\n', 1
            ),
        )
        orch = _orchestrator(tmp_path, root, worktree, feature=True)
        handle = MagicMock(spec=Worktree)
        handle.path = worktree
        for task_id in ("TASK-WEB-1", "TASK-WEB-2", "TASK-ROOT-1"):
            snapshot_task_toolchain(task_id, worktree, root)
        assert orch._carry_coverage_from_worktree(
            "TASK-WEB-1", handle, component="web", when="test"
        ) == ("make web-cov", None)
        assert AutoBuildOrchestrator._read_build_coverage(worktree, "web")[0] == "make web-cov"
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) is None
        # The worktree changes; the later web task keeps the first command.
        _earlier_wave_commits(worktree, _components_with_coverage("make web-other", "x"))
        assert orch._carry_coverage_from_worktree(
            "TASK-WEB-2", handle, component="web", when="test"
        ) == ("make web-cov", None)
        # A root task finds no root entry and never takes the component's.
        assert orch._carry_coverage_from_worktree(
            "TASK-ROOT-1", handle, component=None, when="test"
        ) == (None, None)
        assert load_toolchain_snapshot("TASK-ROOT-1", worktree).coverage is None

    def test_an_unreadable_record_never_falls_back_to_the_live_file(
        self, tmp_path: Path
    ) -> None:
        """Coach review 2 (P15)."""
        worktree = tmp_path / "shared"
        (worktree / ".guardkit").mkdir(parents=True)
        (worktree / ".guardkit" / "config.yaml").write_text(
            'toolchain:\n  test: "make test"\n  coverage: "make live-cov"\n'
        )
        _pin(TASK, worktree, _decl(test="make test"))
        record = AutoBuildOrchestrator._build_coverage_record_path(worktree)
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text('{"": {"coverage": "make first')
        # Reading it says "unreadable", never "nothing recorded".
        with pytest.raises(ValueError):
            AutoBuildOrchestrator._read_build_coverage(worktree, None)
        orch = _orchestrator(tmp_path, worktree, worktree, feature=True)
        handle = MagicMock(spec=Worktree)
        handle.path = worktree
        assert orch._carry_coverage_from_worktree(
            TASK, handle, component=None, when="test"
        ) == (None, None)
        assert load_toolchain_snapshot(TASK, worktree).coverage is None

    def test_a_new_build_forgets_the_record(self, tmp_path: Path) -> None:
        worktree = tmp_path / "shared"
        worktree.mkdir()
        assert AutoBuildOrchestrator._claim_build_coverage(
            worktree, None, "make cov", 60, "TASK-X"
        ) == ("make cov", 60)
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) == ("make cov", 60)
        # The first one stays, and the caller is told which one stands.
        assert AutoBuildOrchestrator._claim_build_coverage(
            worktree, None, "other", 9, "TASK-Y"
        ) == ("make cov", 60)
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) == ("make cov", 60)
        # A new feature worktree (the feature orchestrator's call) forgets it.
        AutoBuildOrchestrator.discard_coach_documents_snapshot(worktree)
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) is None

    def test_a_new_single_task_build_does_not_reuse_an_older_record(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        AutoBuildOrchestrator._claim_build_coverage(
            worktree, None, "make stale-cov", 60, "TASK-OLD"
        )
        result = _run_real_loop(
            _orchestrator(tmp_path, root, worktree), _Turns(worktree, None)
        )
        assert result.final_decision == "configuration_error"
        assert "declares no coverage command" in result.error


class TestDoNothingCoverageCommands:
    @pytest.mark.parametrize(
        "command",
        ["true", " : ", "exit 0", "/bin/true", "echo coverage ok", "true && echo done",
         "printf ok;", "",
         # Coach review 2: a last step that cannot fail, after ; or || or a
         # new line, makes the whole command exit 0 whatever came before.
         "npx vitest run --coverage || true", "npm test; true", "npm test; exit 0",
         "npm run coverage || exit 0", "npm run coverage\ntrue",
         "npm run coverage || echo skipped"],
    )
    def test_refused(self, command) -> None:
        assert does_nothing_command(command) is True

    @pytest.mark.parametrize(
        "command",
        ["npm run coverage", "make coverage-check", COVERAGE_COMMAND,
         "true && go test -cover ./...", "pytest --cov --cov-fail-under=80",
         # Still fails when the first step fails.
         "npm run coverage && true", "npm run coverage && echo done",
         "true || npm run coverage"],
    )
    def test_accepted(self, command) -> None:
        assert does_nothing_command(command) is False

    def test_the_declaring_task_writing_true_stops_after_its_turn(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, NO_COVERAGE + '  coverage: "true"\n')
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 1
        assert turns.coach_receipts == []
        assert result.final_decision == "configuration_error"
        assert "The coverage command `true`" in result.error
        assert "does nothing" in result.error
        assert result.error.startswith("Stopped after the task's turn")
        assert load_toolchain_snapshot(TASK, worktree).coverage is None

    def test_an_earlier_wave_writing_true_stops_the_next_task_before_work(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(worktree, NO_COVERAGE + '  coverage: ":"\n')
        orch = _orchestrator(tmp_path, root, worktree)
        turns = _Turns(worktree, None)
        result = _run_real_loop(orch, turns)
        assert turns.player_turns == 0
        assert result.final_decision == "configuration_error"
        assert "The coverage command `:`" in result.error
        assert "does nothing" in result.error
        assert AutoBuildOrchestrator._read_build_coverage(worktree, None) is None


class TestTheConsoleLine:
    """Coach review 1, surviving mutation B: the operator's console line for a
    coverage stop after the turn names the coverage reason, never the
    task_type advice."""

    def test_after_turn_stop_prints_the_coverage_reason(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, body=DECLARES_CONFIG)
        worktree = _shared_worktree(root, tmp_path / "shared")
        orch = _orchestrator(tmp_path, root, worktree)
        result = _run_real_loop(orch, _Turns(worktree, NO_COVERAGE))
        assert result.final_decision == "configuration_error"
        printed = " ".join(
            str(arg)
            for call in orch._progress_display.console.print.call_args_list
            for arg in call.args
        )
        assert "declares no coverage command" in printed
        assert "Fix the task_type" not in printed
        assert "task file configuration issue" not in printed


# ---------------------------------------------------------------------------
# Review round 2
# ---------------------------------------------------------------------------

COMPONENTS_CANONICAL = (
    'toolchain:\n  test: "make test"\n  components:\n'
    '    web:\n      cwd: web\n      test: "npm test"\n'
    '    api:\n      cwd: api\n      test: "go test ./..."\n'
)


def _components_with_coverage(web: str, api: str) -> str:
    return (
        'toolchain:\n  test: "make test"\n  components:\n'
        f'    web:\n      cwd: web\n      test: "npm test"\n      coverage: "{web}"\n'
        f'    api:\n      cwd: api\n      test: "go test ./..."\n      coverage: "{api}"\n'
    )


class TestTasksOfOneWaveAtTheSameTime:
    """Feature tasks of one wave run at once in one worktree. Two tasks first
    pinning different components' commands must both be recorded."""

    def test_two_components_first_pinned_at_once_both_stand(
        self, tmp_path: Path
    ) -> None:
        import threading
        import time

        from guardkit.orchestrator.toolchain_declaration import (
            snapshot_task_toolchain,
        )

        root = tmp_path / "proj"
        _project(root, body=DECLARES_OTHER, config=COMPONENTS_CANONICAL)
        worktree = _shared_worktree(root, tmp_path / "shared")
        _earlier_wave_commits(worktree, _components_with_coverage("make web-cov", "make api-cov"))
        tasks = {"TASK-WEB-1": "web", "TASK-API-1": "api"}
        for task_id in tasks:
            snapshot_task_toolchain(task_id, worktree, root)
        orch = _orchestrator(tmp_path, root, worktree, feature=True)
        handle = MagicMock(spec=Worktree)
        handle.path = worktree

        # Hold each task inside the record's read-choose-write step for a
        # while, and note when it was there: without the lock the two steps
        # overlap and one task's entry is lost.
        inside: List[tuple] = []
        real_entry = AutoBuildOrchestrator._build_coverage_entry

        def slow_entry(data, component):
            began = time.monotonic()
            time.sleep(0.3)
            inside.append((began, time.monotonic()))
            return real_entry(data, component)

        start = threading.Barrier(len(tasks))
        results: Dict[str, Any] = {}

        def carry(task_id: str, component: str) -> None:
            start.wait(timeout=10)
            results[task_id] = orch._carry_coverage_from_worktree(
                task_id, handle, component=component, when="test"
            )

        with patch.object(
            AutoBuildOrchestrator, "_build_coverage_entry", staticmethod(slow_entry)
        ):
            threads = [
                threading.Thread(target=carry, args=item) for item in tasks.items()
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        assert results == {
            "TASK-WEB-1": ("make web-cov", None),
            "TASK-API-1": ("make api-cov", None),
        }
        (a_start, a_end), (b_start, b_end) = sorted(inside)
        assert a_end <= b_start  # one after the other, never at once
        assert AutoBuildOrchestrator._read_build_coverage(worktree, "web") == ("make web-cov", 300)
        assert AutoBuildOrchestrator._read_build_coverage(worktree, "api") == ("make api-cov", 300)

        # A later Player rewrites both; a later task still gets the first one.
        _earlier_wave_commits(worktree, _components_with_coverage("true", "exit 0"))
        snapshot_task_toolchain("TASK-WEB-2", worktree, root)
        assert orch._carry_coverage_from_worktree(
            "TASK-WEB-2", handle, component="web", when="test"
        ) == ("make web-cov", None)
        assert load_toolchain_snapshot("TASK-WEB-2", worktree).component("web").coverage == "make web-cov"

    def test_a_reader_never_sees_a_part_written_record(self, tmp_path: Path) -> None:
        """The record is replaced whole: no temporary file is left, and the
        file is complete JSON after every claim."""
        worktree = tmp_path / "shared"
        worktree.mkdir()
        for index, scope in enumerate(["", "web", "api", "docs"]):
            AutoBuildOrchestrator._claim_build_coverage(
                worktree, scope or None, f"cov-{index}", 30, f"TASK-{index}"
            )
            record = AutoBuildOrchestrator._build_coverage_record_path(worktree)
            assert json.loads(record.read_text())  # whole, readable
            assert not list(record.parent.glob(record.name + ".*.tmp"))
        assert AutoBuildOrchestrator._read_build_coverage(worktree, "api") == ("cov-2", 30)


class TestASecondBuildOfTheSameTask:
    """The coverage kept on its own (no `toolchain:` block) belongs to the
    build that pinned it: a new build of the same task id never reuses it."""

    def _rebuild(self, root: Path, where: Path, branch: str) -> Path:
        _git(root, "worktree", "remove", "--force", str(where))
        _git(root, "worktree", "add", "-q", "-b", branch, str(where))
        # What the feature orchestrator does when it makes a feature worktree.
        AutoBuildOrchestrator.discard_coach_documents_snapshot(where)
        return where

    def _layout(self, tmp_path: Path, body: str) -> tuple:
        root = tmp_path / "proj"
        _project(root, body=body, config=NO_TOOLCHAIN)
        (root / ".gitignore").write_text(
            ".guardkit/autobuild-private/\n.guardkit/worktrees/\n"
        )
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "ignore worktrees")
        where = root / ".guardkit" / "worktrees" / "FEAT-SETUP"
        worktree = _shared_worktree(root, where)
        return root, worktree

    def test_with_no_declaration_the_old_command_is_not_reused(
        self, tmp_path: Path
    ) -> None:
        root, worktree = self._layout(tmp_path, DECLARES_CONFIG)
        first = _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True),
            _Turns(worktree, NO_TOOLCHAIN + WITH_COVERAGE),
        )
        assert first.final_decision == "approved", first.error
        assert load_coverage_only_pin(TASK, worktree) == (COVERAGE_COMMAND, 120)

        # Build 2 of the same task: nothing declares coverage this time.
        (next((root / "tasks" / "backlog").glob(f"{TASK}*.md"))).write_text(
            f"---\nid: {TASK}\ntitle: Again\ntask_type: feature\n---\n\n{DECLARES_OTHER}"
        )
        worktree = self._rebuild(root, worktree, "autobuild/FEAT-SETUP-2")
        turns = _Turns(worktree, None)
        second = _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), turns
        )
        assert turns.player_turns == 0
        assert second.final_decision == "configuration_error"
        assert "declares no coverage command" in second.error
        assert load_coverage_only_pin(TASK, worktree) is None

    def test_a_changed_declaration_is_used_not_the_old_one(
        self, tmp_path: Path
    ) -> None:
        root, worktree = self._layout(tmp_path, DECLARES_OTHER)
        _earlier_wave_commits(worktree, NO_TOOLCHAIN + WITH_COVERAGE)
        first = _Turns(worktree, None)
        assert _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), first
        ).final_decision == "approved"
        assert first.coach_receipts[0]["command"] == COVERAGE_COMMAND

        worktree = self._rebuild(root, worktree, "autobuild/FEAT-SETUP-2")
        changed = "touch changed-ran.marker && exit 0"
        _earlier_wave_commits(
            worktree,
            NO_TOOLCHAIN + f'toolchain:\n  coverage: "{changed}"\n',
        )
        second = _Turns(worktree, None)
        result = _run_real_loop(
            _orchestrator(tmp_path, root, worktree, feature=True), second
        )
        assert result.final_decision == "approved", result.error
        assert second.coach_receipts[0]["command"] == changed
        assert load_coverage_only_pin(TASK, worktree)[0] == changed

    def test_only_a_fresh_snapshot_clears_it(self, tmp_path: Path) -> None:
        """A resume never takes a fresh snapshot (orchestrate skips it on
        resume), so a resume keeps it; a fresh snapshot of the task clears it."""
        from guardkit.orchestrator.toolchain_declaration import (
            pin_coverage_command,
            snapshot_task_toolchain,
        )

        root = tmp_path / "proj"
        (root / ".guardkit").mkdir(parents=True)
        (root / ".guardkit" / "config.yaml").write_text(NO_TOOLCHAIN)
        worktree = tmp_path / "shared"
        worktree.mkdir()
        assert pin_coverage_command(TASK, worktree, "make cov", 40) == "make cov"
        assert load_coverage_only_pin(TASK, worktree) == ("make cov", 40)
        assert load_coverage_only_pin(TASK, worktree) == ("make cov", 40)
        snapshot_task_toolchain(TASK, worktree, root)
        assert load_coverage_only_pin(TASK, worktree) is None


class TestTheRecordIsWrittenSafely:
    def test_a_failed_write_leaves_the_old_record_whole(self, tmp_path: Path) -> None:
        worktree = tmp_path / "shared"
        worktree.mkdir()
        AutoBuildOrchestrator._claim_build_coverage(worktree, None, "make cov", 60, "T-1")

        def broken_dump(data, out, **kwargs):
            out.write('{"web": {"cov')
            raise OSError("disk full")

        with patch("json.dump", side_effect=broken_dump):
            with pytest.raises(OSError):
                AutoBuildOrchestrator._claim_build_coverage(
                    worktree, "web", "npm run cov", 60, "T-2"
                )
        record = AutoBuildOrchestrator._build_coverage_record_path(worktree)
        assert json.loads(record.read_text()) == {
            "": {"coverage": "make cov", "coverage_timeout": 60, "first_pinned_by": "T-1"}
        }
        assert not list(record.parent.glob(record.name + ".*.tmp"))

    def test_the_task_pins_the_command_that_won(self, tmp_path: Path) -> None:
        """When another task of the wave recorded the scope's command between
        this task's read and its claim, this task pins that one."""
        worktree = tmp_path / "shared"
        (worktree / ".guardkit").mkdir(parents=True)
        (worktree / ".guardkit" / "config.yaml").write_text(
            'toolchain:\n  test: "make test"\n  coverage: "make late-cov"\n'
        )
        _pin(TASK, worktree, _decl(test="make test"))
        AutoBuildOrchestrator._claim_build_coverage(worktree, None, "make first-cov", 70, "T-0")
        orch = _orchestrator(tmp_path, worktree, worktree, feature=True)
        handle = MagicMock(spec=Worktree)
        handle.path = worktree
        with patch.object(
            AutoBuildOrchestrator, "_read_build_coverage", return_value=None
        ):
            assert orch._carry_coverage_from_worktree(
                TASK, handle, component=None, when="test"
            ) == ("make first-cov", None)
        pinned = load_toolchain_snapshot(TASK, worktree)
        assert (pinned.coverage, pinned.coverage_timeout) == ("make first-cov", 70)


class TestCoachReviewTwo:
    def test_a_fresh_snapshot_drops_an_older_builds_declaration(
        self, tmp_path: Path
    ) -> None:
        """A project that removed its toolchain block between builds is not
        judged by the older build's pinned declaration."""
        from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

        root = tmp_path / "proj"
        (root / ".guardkit").mkdir(parents=True)
        (root / ".guardkit" / "config.yaml").write_text(WITH_COVERAGE)
        worktree = tmp_path / "shared"
        worktree.mkdir()
        snapshot_task_toolchain(TASK, worktree, root)
        assert load_toolchain_snapshot(TASK, worktree).coverage == COVERAGE_COMMAND
        (root / ".guardkit" / "config.yaml").write_text(NO_TOOLCHAIN)
        snapshot_task_toolchain(TASK, worktree, root)
        assert load_toolchain_snapshot(TASK, worktree) is None

    def test_the_coachs_stale_probe(self, tmp_path: Path) -> None:
        """Coach review 2's probe_stale.py, as a test: build 2 of the same task
        in a new feature worktree of the same name sees nothing."""
        from guardkit.orchestrator.toolchain_declaration import (
            coverage_view_of_pin,
            pin_coverage_command,
            snapshot_task_toolchain,
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".guardkit").mkdir()
        (repo / ".guardkit" / "config.yaml").write_text(NO_TOOLCHAIN)
        wt = repo / ".guardkit" / "worktrees" / "FEAT-1"
        wt.mkdir(parents=True)
        snapshot_task_toolchain("TASK-A", wt, repo)
        assert pin_coverage_command("TASK-A", wt, "npm run cov-from-rejected-build", 300)
        AutoBuildOrchestrator.discard_coach_documents_snapshot(wt)
        snapshot_task_toolchain("TASK-A", wt, repo)
        assert coverage_view_of_pin("TASK-A", wt) is None
        assert load_coverage_only_pin("TASK-A", wt) is None

    def test_each_work_leg_forgets_an_earlier_legs_record(self, tmp_path: Path) -> None:
        """The task-work route hands its reused checkout in as the worktree;
        building a leg's orchestrator forgets an earlier leg's record."""
        import threading

        from guardkit.orchestrator import work_runner

        checkout = tmp_path / "checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        AutoBuildOrchestrator._claim_build_coverage(checkout, None, "true-ish", 30, "LEG-1")
        assert AutoBuildOrchestrator._read_build_coverage(checkout, None) is not None
        handle = MagicMock(spec=Worktree)
        handle.path = checkout
        work_runner._build_orchestrator(
            repo_root=checkout, worktree=handle, max_turns=1, sdk_timeout=60,
            leg_budget=120, timeout_event=threading.Event(), model=None,
        )
        assert AutoBuildOrchestrator._read_build_coverage(checkout, None) is None
