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

DECLARES_CONFIG = (
    "## Files to Create\n- _none_\n\n"
    "## Files to Modify\n- `.guardkit/config.yaml` — declare the coverage command\n"
    "- `Makefile`\n"
)
DECLARES_OTHER = "## Files to Create\n- `src/greeting.txt`\n\n## Files to Modify\n- _none_\n"


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


def _orchestrator(tmp_path: Path, root: Path, worktree_path: Path):
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
    )
    return orch


def _player_result(turn: int) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=TASK, turn=turn, agent_type="player", success=True,
        report={"task_id": TASK, "turn": turn, "files_modified": [".guardkit/config.yaml"]},
        duration_seconds=1.0, error=None,
    )


def _approve(turn: int) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=TASK, turn=turn, agent_type="coach", success=True,
        report={
            "task_id": TASK, "turn": turn, "decision": "approve", "issues": [],
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
        return _player_result(kwargs.get("turn", self.player_turns))

    def coach(self, *args: Any, **kwargs: Any) -> AgentInvocationResult:
        validator = CoachValidator(str(self.worktree), task_id=kwargs["task_id"])
        self.coach_receipts.append(validator.run_declared_coverage())
        self.coach_test_commands.append(validator._declared_test_command())
        self.coach_had_declaration.append(validator._toolchain is not None)
        return _approve(kwargs["turn"])


def _run_real_loop(orch: AutoBuildOrchestrator, turns: _Turns):
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
            task_id=TASK, requirements="Declare the coverage command",
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
        assert "Makefile" in paths


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
