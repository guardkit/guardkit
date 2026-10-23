"""A task that needs coverage stops at task start when no coverage command is declared.

Since 19 September 2026 a feature, refactor, glue or wiring task passes only on
a MEASURED coverage, and only the project's declared ``toolchain.coverage``
command measures it. A project that declares none could therefore never pass
such a task, but GuardKit found out one refused turn at a time and ended in a
"no file changes" stall that said the task might not be doable as written
(19 October 2026). Now the task stops before any model call, as a
configuration error that says what to add.

Checked here:

* the decision, across the task types that need coverage and those that do
  not, declared and undeclared, root block and component, and the direct-mode
  relaxation; it agrees with the Coach's own resolution of the declared
  command and of which types need coverage;
* ``orchestrate`` stops such a task with no Player, Coach or planning call,
  zero turns and the plain message, and the summary and error say it plainly
  (not "fix the task_type", not "cannot be done as written");
* a project that declares a coverage command, a direct-mode task and a task
  type that does not need coverage all reach the loop exactly as before.

Invented projects only; no model is called.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.models.task_types import (
    DEFAULT_PROFILES,
    TASK_TYPE_ALIASES,
    TaskType,
    get_profile,
)
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import (
    ToolchainDeclaration,
    declared_coverage_command,
    undeclared_coverage_refusal,
)
from guardkit.worktrees.manager import Worktree

pytestmark = pytest.mark.coverage_declaration_check

COVERAGE_TYPES = ["feature", "refactor", "glue", "wiring"]
OTHER_TYPES = [
    t.value for t in TaskType if not DEFAULT_PROFILES[t].coverage_required
]


def _decl(**raw: Any) -> ToolchainDeclaration:
    return ToolchainDeclaration.model_validate(raw)


ROOT_ONLY = _decl(test="make test", coverage="make coverage-check")
NOTHING = _decl(test="make test", lint="make lint")
COMPONENTS = _decl(
    test="make test",
    components={
        "web": {"cwd": "web", "test": "npm test", "coverage": "npm run cov"},
        "api": {"cwd": "api", "test": "go test ./..."},
    },
)
ROOT_AND_BARE_COMPONENT = _decl(
    test="make test",
    coverage="make coverage-check",
    components={"api": {"cwd": "api", "test": "go test ./..."}},
)


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------


class TestDecision:
    def test_the_types_that_need_coverage_are_unchanged(self) -> None:
        needing = sorted(
            t.value for t in TaskType if DEFAULT_PROFILES[t].coverage_required
        )
        assert needing == sorted(COVERAGE_TYPES)

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES + [None])
    @pytest.mark.parametrize(
        "toolchain", [None, NOTHING], ids=["no-toolchain-block", "no-coverage-key"]
    )
    def test_undeclared_root_coverage_is_refused(self, task_type, toolchain) -> None:
        refusal = undeclared_coverage_refusal(task_type=task_type, toolchain=toolchain)
        assert refusal is not None
        assert "declares no coverage command" in refusal
        assert "`toolchain.coverage`" in refusal
        assert 'coverage: "<command that exits 0 when the coverage threshold is met>"' in refusal
        assert "under `toolchain:`" in refusal
        assert f"a {task_type or 'feature'} task" in refusal
        assert "feature, refactor, glue or wiring" in refusal
        assert "other task types are unaffected" in refusal

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES + [None])
    def test_declared_root_coverage_passes(self, task_type) -> None:
        assert undeclared_coverage_refusal(task_type=task_type, toolchain=ROOT_ONLY) is None

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES)
    def test_component_with_its_own_coverage_passes(self, task_type) -> None:
        assert (
            undeclared_coverage_refusal(
                task_type=task_type, toolchain=COMPONENTS, component="web"
            )
            is None
        )

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES)
    def test_component_without_coverage_is_refused_even_when_root_declares_it(
        self, task_type
    ) -> None:
        refusal = undeclared_coverage_refusal(
            task_type=task_type, toolchain=ROOT_AND_BARE_COMPONENT, component="api"
        )
        assert refusal is not None
        assert "for the task's component `api`" in refusal
        assert "`toolchain.components.api.coverage`" in refusal
        assert "under `toolchain.components.api:`" in refusal

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES)
    def test_root_task_does_not_borrow_a_components_coverage(self, task_type) -> None:
        assert (
            undeclared_coverage_refusal(task_type=task_type, toolchain=COMPONENTS)
            is not None
        )

    @pytest.mark.parametrize("task_type", OTHER_TYPES)
    @pytest.mark.parametrize("toolchain", [None, NOTHING, COMPONENTS])
    def test_types_that_do_not_need_coverage_are_unaffected(
        self, task_type, toolchain
    ) -> None:
        assert undeclared_coverage_refusal(task_type=task_type, toolchain=toolchain) is None
        assert (
            undeclared_coverage_refusal(
                task_type=task_type, toolchain=COMPONENTS, component="api"
            )
            is None
        )

    @pytest.mark.parametrize("alias", sorted(TASK_TYPE_ALIASES))
    def test_aliases_follow_the_type_they_stand_for(self, alias) -> None:
        refusal = undeclared_coverage_refusal(task_type=alias, toolchain=None)
        assert (refusal is not None) == DEFAULT_PROFILES[
            TASK_TYPE_ALIASES[alias]
        ].coverage_required
        if refusal is not None:
            assert f"(task_type: {alias})" in refusal

    @pytest.mark.parametrize("bad", ["not-a-real-task-type", "", 7, ["feature"]])
    def test_an_invalid_type_is_left_to_the_coachs_own_stop(self, bad) -> None:
        assert undeclared_coverage_refusal(task_type=bad, toolchain=None) is None

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES)
    def test_direct_mode_is_the_named_relaxation(self, task_type) -> None:
        assert (
            undeclared_coverage_refusal(
                task_type=task_type, toolchain=None, implementation_mode="direct"
            )
            is None
        )
        # Only the exact value the router sends to the direct Player.
        for mode in ("task-work", "Direct", None):
            assert (
                undeclared_coverage_refusal(
                    task_type=task_type, toolchain=None, implementation_mode=mode
                )
                is not None
            )

    def test_no_task_type_reads_as_feature(self) -> None:
        refusal = undeclared_coverage_refusal(task_type=None, toolchain=None)
        assert "a task with no task_type is a feature task" in refusal


class TestSameAnswerAsTheCoach:
    """The task-start answer must be the answer the Coach gives every turn."""

    @pytest.mark.parametrize(
        "toolchain,component",
        [
            (None, None),
            (NOTHING, None),
            (ROOT_ONLY, None),
            (COMPONENTS, None),
            (COMPONENTS, "web"),
            (COMPONENTS, "api"),
            (COMPONENTS, "missing"),
            (ROOT_AND_BARE_COMPONENT, "api"),
            (ROOT_AND_BARE_COMPONENT, None),
        ],
    )
    def test_declared_command_matches_the_coach(
        self, tmp_path: Path, toolchain, component
    ) -> None:
        validator = CoachValidator(
            str(tmp_path), toolchain=toolchain, component=component
        )
        assert declared_coverage_command(toolchain, component) == (
            validator._declared_coverage_command()
        )

    @pytest.mark.parametrize(
        "raw",
        [None] + [t.value for t in TaskType] + sorted(TASK_TYPE_ALIASES),
    )
    def test_which_types_need_coverage_matches_the_coach(
        self, tmp_path: Path, raw
    ) -> None:
        validator = CoachValidator(str(tmp_path))
        resolved = validator._resolve_task_type({"task_type": raw})
        coach_needs = get_profile(resolved).coverage_required
        assert (
            undeclared_coverage_refusal(task_type=raw, toolchain=None) is not None
        ) == coach_needs


# ---------------------------------------------------------------------------
# orchestrate(): stopped before any model call
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Coverage Test",
         "-c", "user.email=coverage@example.invalid", *args],
        check=True, capture_output=True, text=True,
    )


def _project(
    root: Path,
    *,
    toolchain_yaml: str,
    task_type: Optional[str] = "refactor",
    implementation_mode: Optional[str] = None,
    component: Optional[str] = None,
    task_id: str = "TASK-COV-001",
    body: str = "Reqs.\n",
    frontmatter_extra: Optional[list] = None,
) -> None:
    """An invented project: a config, one task file, in a git repository."""
    (root / ".guardkit").mkdir(parents=True, exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(toolchain_yaml, encoding="utf-8")
    front = [f"id: {task_id}", "title: Tidy the greeting module"]
    if task_type is not None:
        front.append(f"task_type: {task_type}")
    if implementation_mode is not None:
        front.append(f"implementation_mode: {implementation_mode}")
    if component is not None:
        front.append(f"component: {component}")
    front.extend(frontmatter_extra or [])
    tasks = root / "tasks" / "backlog"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / f"{task_id}-tidy.md").write_text(
        "---\n" + "\n".join(front) + "\n---\n\n# Tidy\n\n" + body, encoding="utf-8"
    )
    (root / ".gitignore").write_text(".guardkit/autobuild-private/\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    _git(root, "checkout", "-q", "-b", "autobuild/work")


NO_COVERAGE = "toolchain:\n  test: \"make test\"\n  lint: \"make lint\"\n"
WITH_COVERAGE = (
    "toolchain:\n  test: \"make test\"\n  coverage: \"make coverage-check\"\n"
)


def _orchestrator(tmp_path: Path, root: Path, *, ablation_mode: bool = False):
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    worktree = MagicMock(spec=Worktree)
    worktree.task_id = "TASK-COV-001"
    worktree.path = root
    worktree.branch_name = "autobuild/TASK-COV-001"
    worktree.base_branch = "main"
    manager = MagicMock()
    manager.create.return_value = worktree
    manager.worktrees_dir = tmp_path / "worktrees"
    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(side_effect=AssertionError("Player must not run"))
    invoker.invoke_coach = AsyncMock(side_effect=AssertionError("Coach must not run"))
    gates = MagicMock()
    pre_loop_calls: list[Any] = []

    async def execute(*args: Any, **kwargs: Any) -> PreLoopResult:
        pre_loop_calls.append(args)
        return PreLoopResult(
            plan={"steps": []}, plan_path="/tmp/plan.md", complexity=3, max_turns=3,
            checkpoint_passed=True, architectural_score=90, clarifications={},
        )

    gates.execute = execute
    orch = AutoBuildOrchestrator(
        repo_root=root,
        max_turns=3,
        worktree_manager=manager,
        agent_invoker=invoker,
        progress_display=MagicMock(),
        pre_loop_gates=gates,
        enable_checkpoints=False,
        enable_context=False,
        ablation_mode=ablation_mode,
    )
    return orch, invoker, pre_loop_calls


def _run(
    orch: AutoBuildOrchestrator,
    task_id: str = "TASK-COV-001",
    task_file_path: Optional[Path] = None,
):
    return orch.orchestrate(
        task_id=task_id, requirements="reqs", acceptance_criteria=["AC-001: x"],
        task_file_path=task_file_path,
    )


class TestStoppedAtTaskStart:
    def test_refactor_task_without_declared_coverage_stops_before_any_model_call(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, toolchain_yaml=NO_COVERAGE, task_type="refactor")
        orch, invoker, pre_loop_calls = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase",
            side_effect=AssertionError("the loop must not start"),
        ):
            result = _run(orch)
        assert result.success is False
        assert result.final_decision == "configuration_error"
        assert result.total_turns == 0
        assert result.turn_history == []
        assert result.error.startswith("This project declares no coverage command")
        assert "a refactor task needs measured coverage" in result.error
        assert 'coverage: "<command that exits 0' in result.error
        invoker.invoke_player.assert_not_called()
        invoker.invoke_coach.assert_not_called()
        assert pre_loop_calls == []  # no planning model call either

    def test_summary_and_error_say_it_plainly(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, toolchain_yaml=NO_COVERAGE, task_type="feature")
        orch, _, _ = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_build_summary_details",
            autospec=True, side_effect=AutoBuildOrchestrator._build_summary_details,
        ) as summary:
            result = _run(orch)
        assert result.final_decision == "configuration_error"
        rendered = [
            AutoBuildOrchestrator._build_summary_details(*c.args)
            for c in summary.call_args_list
        ]
        message = orch._build_error_message("configuration_error", [])
        assert rendered
        for text in rendered + [message]:
            assert "declares no coverage command" in text
            assert "Fix the task_type" not in text
            assert "fix task_type" not in text
            assert "cannot be done as written" not in text
            assert "unknown configuration error" not in text
            assert "stall" not in text.lower()

    def test_component_task_is_judged_by_its_component(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(
            root,
            toolchain_yaml=(
                "toolchain:\n  test: \"make test\"\n  coverage: \"make cov\"\n"
                "  components:\n    api:\n      cwd: api\n      test: \"make test\"\n"
            ),
            task_type="wiring",
            component="api",
        )
        orch, invoker, _ = _orchestrator(tmp_path, root)
        result = _run(orch)
        assert result.final_decision == "configuration_error"
        assert "for the task's component `api`" in result.error
        invoker.invoke_player.assert_not_called()

    def test_a_fresh_run_forgets_the_previous_runs_refusal(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(root, toolchain_yaml=NO_COVERAGE)
        orch, _, _ = _orchestrator(tmp_path, root)
        _run(orch)
        assert orch._coverage_declaration_refusal
        (root / ".guardkit" / "config.yaml").write_text(WITH_COVERAGE)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase", return_value=([], "max_turns_exceeded")
        ):
            result = _run(orch)
        assert orch._coverage_declaration_refusal is None
        assert result.final_decision == "max_turns_exceeded"


class TestWhatTheRecordsReceive:
    """The factory reads the task-failed event, the build-outcome record and
    the saved task state, not only the returned result."""

    def test_event_outcome_and_task_state_carry_the_stop(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(root, toolchain_yaml=NO_COVERAGE, task_type="glue")
        task_file = next((root / "tasks" / "backlog").glob("TASK-COV-001*.md"))
        orch, _, _ = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_capture_build_outcome", autospec=True
        ) as outcome, patch.object(
            AutoBuildOrchestrator, "_emit_task_failed", autospec=True
        ) as failed, patch.object(
            AutoBuildOrchestrator, "_save_state", autospec=True
        ) as saved:
            result = _run(orch, task_file_path=task_file)
        assert result.final_decision == "configuration_error"

        failed.assert_called_once_with(orch, "TASK-COV-001", "configuration_error")

        outcome.assert_called_once()
        kwargs = outcome.call_args.kwargs
        assert outcome.call_args.args[1:] == ("TASK-COV-001",)
        assert kwargs["success"] is False
        assert kwargs["final_decision"] == "configuration_error"
        assert kwargs["turn_history"] == []
        assert kwargs["error"] == result.error
        assert "declares no coverage command" in kwargs["error"]

        assert saved.call_args_list[-1].args[1] == task_file
        assert saved.call_args_list[-1].args[3] == "blocked"
        assert all(c.args[3] != "in_review" for c in saved.call_args_list)


class TestUnchangedWhenTheTaskCanPass:
    def test_ablation_mode_is_not_stopped(self, tmp_path: Path) -> None:
        """Ablation skips the Coach and approves every turn, so the coverage
        gate never judges the task and it is not stopped."""
        root = tmp_path / "proj"
        _project(root, toolchain_yaml=NO_COVERAGE, task_type="refactor")
        orch, _, _ = _orchestrator(tmp_path, root, ablation_mode=True)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase", return_value=([], "approved")
        ) as loop:
            result = _run(orch)
        loop.assert_called_once()
        assert result.final_decision == "approved"
        assert orch._coverage_declaration_refusal is None


    @pytest.mark.parametrize(
        "toolchain_yaml,task_type,mode",
        [
            (WITH_COVERAGE, "refactor", None),
            (WITH_COVERAGE, None, None),
            (NO_COVERAGE, "refactor", "direct"),
            (NO_COVERAGE, "testing", None),
            (NO_COVERAGE, "documentation", None),
            (NO_COVERAGE, "not-a-real-task-type", None),
        ],
        ids=[
            "declared-coverage", "declared-no-task-type", "direct-mode",
            "testing-type", "documentation-type", "invalid-type-left-to-coach",
        ],
    )
    def test_reaches_the_loop(
        self, tmp_path: Path, toolchain_yaml, task_type, mode
    ) -> None:
        root = tmp_path / "proj"
        _project(
            root, toolchain_yaml=toolchain_yaml, task_type=task_type,
            implementation_mode=mode,
        )
        orch, _, _ = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase", return_value=([], "max_turns_exceeded")
        ) as loop:
            result = _run(orch)
        loop.assert_called_once()
        assert loop.call_args.kwargs["task_type"] == task_type
        assert result.final_decision == "max_turns_exceeded"
        assert orch._coverage_declaration_refusal is None


# ---------------------------------------------------------------------------
# 23 October 2026: a task that writes no source code needs no coverage
# ---------------------------------------------------------------------------
#
# Builds stopped before any work on tasks that only wrote deployment
# configuration (a compose file, a deploy folder) because the planner called
# them feature tasks. Coverage has nothing to measure in such a task, whatever
# its type, so it is neither stopped at task start nor held at "Coverage is
# UNKNOWN" by the Coach. Decided by file kind, never by project or language.

from guardkit.orchestrator.toolchain_declaration import (  # noqa: E402
    declares_no_source_files,
    is_non_source_file,
)

CONFIG_ONLY = [
    "deploy/compose.yaml",
    "compose.yaml",
    "deploy/Dockerfile",
    "Dockerfile.dev",
    "deploy/.env.example",
    "README.md",
    "docs/deploy.rst",
    "package-lock.json",
    "deploy/settings.toml",
    "infra/main.tf",
    "data/seed.csv",
]
CONFIG_ONLY_SECTIONS = (
    "## Files to Create\n- `deploy/compose.yaml` — the stack\n"
    "- `deploy/Dockerfile`\n- `deploy/.env.example`\n\n"
    "## Files to Modify\n- `README.md` — how to deploy\n"
)
WITH_ONE_SOURCE_FILE = CONFIG_ONLY_SECTIONS + "- `src/server.go`\n"


class TestFileKinds:
    @pytest.mark.parametrize("path", CONFIG_ONLY + [
        "Containerfile", "app.dockerfile", ".gitignore", ".dockerignore",
        "LICENSE", "config/app.yml", "pom.xml", "yarn.lock", "go.sum",
        "`deploy/compose.yaml`", "deploy\\compose.yaml", "logo.svg",
        # deployment scripts, make files, service units, version pins
        "scripts/deploy.sh", "lib.bash", "env.zsh", "Makefile", "GNUmakefile",
        "rules.mk", "CMakeLists.txt", "requirements.txt", "notes.txt",
        "deploy/systemd/app.service", "app.timer", "deploy/Caddyfile",
        "deploy/crontab", ".tool-versions", ".nvmrc",
        # a template or example is the kind of the file it stands for
        "deploy/settings.sh.template", "deploy/profile.yaml.template",
        "nginx.conf.tmpl", "config.json.example", "app.ini.sample",
        "phpunit.xml.dist",
    ])
    def test_not_source(self, path: str) -> None:
        assert is_non_source_file(path) is True

    @pytest.mark.parametrize("path", [
        "src/server.go", "app/main.py", "web/index.ts", "lib/thing.rs",
        "migrations/001.sql", "web/styles.css", "web/index.html",
        "src/main.py.template", "foo.template", ".template",
        "deploy/", "deploy", "src/unknown.kind", "", None, 3,
    ])
    def test_source_or_unknown(self, path: Any) -> None:
        assert is_non_source_file(path) is False

    def test_every_file_of_the_shipped_deploy_kit_is_not_source(self) -> None:
        """The deploy kit GuardKit itself ships: a task that copies it into a
        project writes no source code."""
        kit = (
            Path(__file__).resolve().parents[2]
            / "installer" / "core" / "templates" / "common" / "deploy"
        )
        files = [p for p in kit.rglob("*") if p.is_file()]
        assert files, f"no deploy kit found at {kit}"
        source = [
            p.relative_to(kit).as_posix() for p in files
            if not is_non_source_file(p.relative_to(kit).as_posix())
        ]
        assert source == []
        assert declares_no_source_files(
            [f"deploy/{p.relative_to(kit).as_posix()}" for p in files]
        )

    def test_any_source_file_makes_the_task_a_source_task(self) -> None:
        assert declares_no_source_files(CONFIG_ONLY) is True
        assert declares_no_source_files(CONFIG_ONLY + ["src/server.go"]) is False

    @pytest.mark.parametrize("paths", [None, [], ["", "  "], [None, 3]])
    def test_a_task_that_declares_no_files_is_not_known_to_be_clean(
        self, paths: Any
    ) -> None:
        assert declares_no_source_files(paths) is False


class TestNoSourceFilesDecision:
    @pytest.mark.parametrize("task_type", COVERAGE_TYPES + [None])
    def test_config_only_task_is_not_refused(self, task_type) -> None:
        assert undeclared_coverage_refusal(
            task_type=task_type, toolchain=NOTHING, declared_paths=CONFIG_ONLY
        ) is None

    @pytest.mark.parametrize("task_type", COVERAGE_TYPES)
    def test_one_source_file_keeps_the_refusal(self, task_type) -> None:
        refusal = undeclared_coverage_refusal(
            task_type=task_type, toolchain=NOTHING,
            declared_paths=CONFIG_ONLY + ["src/server.go"],
        )
        assert refusal is not None
        assert "declares no coverage command" in refusal

    @pytest.mark.parametrize("paths", [None, []])
    def test_no_declared_files_keeps_the_refusal(self, paths) -> None:
        assert undeclared_coverage_refusal(
            task_type="feature", toolchain=NOTHING, declared_paths=paths
        ) is not None

    def test_the_component_rule_is_unchanged_for_source_tasks(self) -> None:
        refusal = undeclared_coverage_refusal(
            task_type="wiring", toolchain=COMPONENTS, component="api",
            declared_paths=["api/handler.go", "api/config.yaml"],
        )
        assert "for the task's component `api`" in refusal

    def test_the_refusal_names_the_exception(self) -> None:
        refusal = undeclared_coverage_refusal(task_type="feature", toolchain=None)
        assert "tasks that change only configuration, deployment" in refusal


class TestNoSourceFilesAtTaskStart:
    @pytest.mark.parametrize("task_type", ["feature", "refactor", None])
    def test_config_only_task_reaches_the_loop(
        self, tmp_path: Path, task_type
    ) -> None:
        root = tmp_path / "proj"
        _project(
            root, toolchain_yaml=NO_COVERAGE, task_type=task_type,
            body=CONFIG_ONLY_SECTIONS,
        )
        orch, _, _ = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase", return_value=([], "max_turns_exceeded")
        ) as loop:
            result = _run(orch)
        loop.assert_called_once()
        assert result.final_decision == "max_turns_exceeded"
        assert orch._coverage_declaration_refusal is None
        assert orch._coverage_due_from_task is None
        # Kept for the Coach, which makes the same exception.
        assert set(orch._declared_task_paths) == {
            "deploy/compose.yaml", "deploy/Dockerfile", "deploy/.env.example",
            "README.md",
        }

    def test_files_listed_in_frontmatter_count_too(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        _project(
            root, toolchain_yaml=NO_COVERAGE, task_type="feature",
            frontmatter_extra=["files_to_create:", "  - compose.yaml"],
        )
        orch, _, _ = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase", return_value=([], "max_turns_exceeded")
        ) as loop:
            _run(orch)
        loop.assert_called_once()

    def test_a_task_with_one_source_file_still_stops_before_any_work(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "proj"
        _project(
            root, toolchain_yaml=NO_COVERAGE, task_type="feature",
            body=WITH_ONE_SOURCE_FILE,
        )
        orch, invoker, pre_loop_calls = _orchestrator(tmp_path, root)
        with patch.object(
            AutoBuildOrchestrator, "_loop_phase",
            side_effect=AssertionError("the loop must not start"),
        ):
            result = _run(orch)
        assert result.final_decision == "configuration_error"
        assert result.total_turns == 0
        assert "a feature task needs measured coverage" in result.error
        invoker.invoke_player.assert_not_called()
        assert pre_loop_calls == []


def _gate_results(**overrides: Any) -> dict:
    """A task-work results block whose every gate but coverage passes."""
    results: dict = {
        "task_id": "TASK-COV-001",
        "completed": True,
        "quality_gates": {"all_passed": True, "tests_failed": 0},
        "code_review": {"score": 95},
        "plan_audit": {"status": "passed", "violations": 0},
    }
    results.update(overrides)
    return results


class TestNoSourceFilesInTheCoach:
    """The Coach's half: the same exception, checked against what the
    builder actually wrote as well as what the task declared."""

    def _gates(
        self, tmp_path: Path, declared, results, toolchain=None, peers=None
    ):
        validator = CoachValidator(
            str(tmp_path), toolchain=toolchain, task_id="TASK-COV-001",
            peer_changed_files=peers,
        )
        return validator.verify_quality_gates(
            results, profile=get_profile(TaskType.FEATURE),
            declared_files=declared,
        )

    def test_config_only_task_is_relaxed_by_name(self, tmp_path: Path) -> None:
        gates = self._gates(
            tmp_path, CONFIG_ONLY,
            _gate_results(files_authored=["deploy/compose.yaml", "README.md"]),
        )
        assert gates.coverage_relaxed_by == "no_source_files"
        assert gates.coverage_met is True
        assert gates.all_gates_passed is True

    def test_legacy_record_without_files_authored_reads_created_and_modified(
        self, tmp_path: Path
    ) -> None:
        gates = self._gates(
            tmp_path, CONFIG_ONLY,
            _gate_results(
                files_created=["deploy/compose.yaml"], files_modified=["README.md"]
            ),
        )
        assert gates.coverage_relaxed_by == "no_source_files"

    def test_a_source_file_the_builder_wrote_keeps_coverage_unknown(
        self, tmp_path: Path
    ) -> None:
        gates = self._gates(
            tmp_path, CONFIG_ONLY,
            _gate_results(files_authored=["deploy/compose.yaml", "src/server.go"]),
        )
        assert gates.coverage_relaxed_by is None
        assert gates.coverage_met is None
        assert gates.all_gates_passed is False

    def test_a_source_file_a_shell_command_wrote_keeps_coverage_unknown(
        self, tmp_path: Path
    ) -> None:
        """The builder's file tools wrote only the compose file, but a shell
        command (``cat > src/server.go``) wrote source code, which only the
        created and modified lists show."""
        gates = self._gates(
            tmp_path, ["deploy/compose.yaml"],
            _gate_results(
                files_authored=["deploy/compose.yaml"],
                files_authored_tracking="tracked",
                shell_command_tool_uses=3,
                files_created=["deploy/compose.yaml", "src/server.go"],
            ),
        )
        assert gates.coverage_relaxed_by is None
        assert gates.coverage_met is None
        assert gates.all_gates_passed is False

    def test_a_source_file_only_another_wave_task_changed_is_set_aside(
        self, tmp_path: Path
    ) -> None:
        results = _gate_results(
            files_authored=["deploy/compose.yaml"],
            files_authored_tracking="tracked",
            files_modified=["deploy/compose.yaml", "src/server.go"],
        )
        gates = self._gates(
            tmp_path, ["deploy/compose.yaml"], results,
            peers={"TASK-COV-002": ["src/server.go"]},
        )
        assert gates.coverage_relaxed_by == "no_source_files"
        # Without the peer's record the same file refuses the exception.
        gates = self._gates(tmp_path, ["deploy/compose.yaml"], results)
        assert gates.coverage_relaxed_by is None

    def test_a_validator_that_cannot_answer_fails_closed(
        self, tmp_path: Path
    ) -> None:
        validator = CoachValidator(str(tmp_path))
        with patch.object(
            CoachValidator, "_declared_coverage_command", side_effect=AttributeError
        ):
            assert validator._touches_no_source_files(
                ["compose.yaml"], _gate_results(files_authored=["compose.yaml"])
            ) is False

    @pytest.mark.parametrize("declared", [
        None, [], CONFIG_ONLY + ["src/server.go"],
    ])
    def test_declared_source_or_nothing_declared_keeps_coverage_unknown(
        self, tmp_path: Path, declared
    ) -> None:
        gates = self._gates(
            tmp_path, declared, _gate_results(files_authored=["compose.yaml"])
        )
        assert gates.coverage_relaxed_by is None
        assert gates.coverage_met is None

    def test_a_declared_coverage_command_still_decides(
        self, tmp_path: Path
    ) -> None:
        gates = self._gates(
            tmp_path, CONFIG_ONLY,
            _gate_results(files_authored=["compose.yaml"]),
            toolchain=ROOT_ONLY,
        )
        assert gates.coverage_relaxed_by is None
        assert gates.coverage_met is None  # left for the declared command

    def test_an_unrecorded_authored_set_is_not_taken_as_clean(
        self, tmp_path: Path
    ) -> None:
        gates = self._gates(
            tmp_path, CONFIG_ONLY,
            # An empty list without the tracking marker: never recorded.
            _gate_results(files_authored=[]),
        )
        assert gates.coverage_relaxed_by is None


class TestTheCoachIsToldTheDeclaredFiles:
    """Both Coach paths hand the task's declared files to the validator."""

    def _capture(self, tmp_path: Path, method: str, declared):
        orch = AutoBuildOrchestrator(
            repo_root=tmp_path, enable_pre_loop=False,
            worktree_manager=MagicMock(), enable_context=False,
        )
        orch._declared_task_paths = declared
        seen: list = []

        def capture(self, *args: Any, **kwargs: Any):
            seen.append(kwargs["task"])
            raise RuntimeError("captured")

        worktree = MagicMock(spec=Worktree)
        worktree.path = tmp_path
        target = "gather_evidence" if method == "_invoke_coach_primary" else "validate"
        with patch.object(CoachValidator, target, capture), patch.object(
            CoachValidator, "_is_docker_available", return_value=False
        ):
            try:
                getattr(orch, method)(
                    task_id="TASK-COV-001", turn=1, requirements="reqs",
                    player_report={"task_id": "TASK-COV-001"},
                    worktree=worktree, acceptance_criteria=["AC-001: x"],
                    task_type="feature", skip_arch_review=True,
                    requires_infrastructure=None, consumer_context=None,
                    remaining_budget=None, wave_size=1, peer_changed_files=None,
                    context_prompt="", start_time=0.0,
                )
            except Exception:  # noqa: BLE001 - only the handed-over task matters
                pass
        assert seen, f"{method} never reached the validator"
        return seen[0]

    @pytest.mark.parametrize("method", ["_invoke_coach_primary", "_invoke_coach_legacy"])
    def test_declared_files_reach_the_validator(
        self, tmp_path: Path, method: str
    ) -> None:
        task = self._capture(tmp_path, method, ["compose.yaml", "README.md"])
        assert task["declared_files"] == ["compose.yaml", "README.md"]

    @pytest.mark.parametrize("method", ["_invoke_coach_primary", "_invoke_coach_legacy"])
    def test_no_declared_files_leaves_the_task_unchanged(
        self, tmp_path: Path, method: str
    ) -> None:
        task = self._capture(tmp_path, method, [])
        assert "declared_files" not in task
