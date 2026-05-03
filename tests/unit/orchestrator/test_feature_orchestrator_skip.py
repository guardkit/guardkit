"""FeatureOrchestrator short-circuits operator_handoff tasks (TASK-FPTC-003).

Pins AC-FPTC-003-01 through AC-FPTC-003-04: a fixture task with
``task_type: operator_handoff`` in its YAML frontmatter must be reported
as deferred WITHOUT invoking the Player/Coach loop. The deferred outcome
is terminal-but-not-failed, distinct from BLOCKED/FAILED/COMPLETED, and
carries the canonical reason string ``"operator follow-up — runtime
verification required"``.

Coverage Target: >=85%
"""

from __future__ import annotations

import asyncio
import tempfile
import yaml
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureLoader,
    FeatureOrchestration,
    FeatureTask,
)
from guardkit.worktrees import Worktree


HANDOFF_REASON = "operator follow-up — runtime verification required"


# ============================================================================
# Fixtures
# ============================================================================


def _write_task_md(
    repo_root: Path,
    rel_path: str,
    task_id: str,
    title: str,
    task_type: str,
) -> Path:
    """Write a task markdown file with the given ``task_type`` frontmatter."""
    task_file = repo_root / rel_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        dedent(
            f"""\
            ---
            id: {task_id}
            title: "{title}"
            status: backlog
            task_type: {task_type}
            ---

            # Task: {title}

            Body.
            """
        )
    )
    return task_file


@pytest.fixture
def handoff_feature() -> Feature:
    """Provide a Feature whose only task is an operator_handoff."""
    return Feature(
        id="FEAT-HANDOFF",
        name="Handoff Feature",
        description="Feature with a single operator_handoff task",
        created="2026-05-03T12:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-FPTC-OP1",
                name="Rotate production credentials",
                file_path=Path("tasks/backlog/TASK-FPTC-OP1.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=15,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-FPTC-OP1"]],
            estimated_duration_minutes=15,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def mixed_feature() -> Feature:
    """Provide a Feature with one feature task + one operator_handoff."""
    return Feature(
        id="FEAT-MIXED",
        name="Mixed Feature",
        description="One normal feature task + one operator_handoff",
        created="2026-05-03T12:00:00Z",
        status="planned",
        complexity=4,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-FPTC-N1",
                name="Normal feature task",
                file_path=Path("tasks/backlog/TASK-FPTC-N1.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-FPTC-H1",
                name="Hand off to operator",
                file_path=Path("tasks/backlog/TASK-FPTC-H1.md"),
                complexity=2,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=10,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-FPTC-N1", "TASK-FPTC-H1"]],
            estimated_duration_minutes=40,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def handoff_repo(handoff_feature, tmp_path) -> Path:
    """Repo with feature YAML + a single operator_handoff task file."""
    repo_root = tmp_path
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = FeatureLoader._feature_to_dict(handoff_feature)
    (features_dir / "FEAT-HANDOFF.yaml").write_text(yaml.dump(feature_data))

    _write_task_md(
        repo_root,
        "tasks/backlog/TASK-FPTC-OP1.md",
        "TASK-FPTC-OP1",
        "Rotate production credentials",
        "operator_handoff",
    )
    return repo_root


@pytest.fixture
def mixed_repo(mixed_feature, tmp_path) -> Path:
    """Repo with feature YAML + one normal feature task + one operator_handoff."""
    repo_root = tmp_path
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = FeatureLoader._feature_to_dict(mixed_feature)
    (features_dir / "FEAT-MIXED.yaml").write_text(yaml.dump(feature_data))

    _write_task_md(
        repo_root,
        "tasks/backlog/TASK-FPTC-N1.md",
        "TASK-FPTC-N1",
        "Normal feature task",
        "feature",
    )
    _write_task_md(
        repo_root,
        "tasks/backlog/TASK-FPTC-H1.md",
        "TASK-FPTC-H1",
        "Hand off to operator",
        "operator_handoff",
    )
    return repo_root


@pytest.fixture
def mock_worktree(tmp_path) -> Worktree:
    """Provide a mock Worktree."""
    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-MOCK"
    worktree_path.mkdir(parents=True, exist_ok=True)
    return Worktree(
        task_id="FEAT-MOCK",
        branch_name="autobuild/FEAT-MOCK",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def mock_worktree_manager(tmp_path, mock_worktree):
    """Provide a mock WorktreeManager."""
    manager = MagicMock()
    manager.create.return_value = mock_worktree
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    manager.worktrees_dir = worktrees_dir
    return manager


# ============================================================================
# AC-FPTC-003-01 / AC-FPTC-003-04: skip branch short-circuits dispatch
# ============================================================================


class TestOperatorHandoffSkipBranch:
    """AC-FPTC-003-01 + AC-FPTC-003-04: handoff tasks skip Player/Coach."""

    def test_operator_handoff_yields_deferred_result_without_dispatch(
        self, handoff_repo, handoff_feature, mock_worktree, mock_worktree_manager
    ):
        """Handoff task → deferred result; _execute_task is never called."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )

        # If dispatch were to fire, this would assert. Patching _execute_task
        # is the strongest check that the Player/Coach loop never starts —
        # _execute_task is the single dispatch site that constructs the
        # AutoBuildOrchestrator and burns the SDK budget.
        with patch.object(
            orchestrator, "_execute_task"
        ) as mock_execute_task:
            results = asyncio.run(
                orchestrator._execute_wave_parallel(
                    wave_number=1,
                    task_ids=["TASK-FPTC-OP1"],
                    feature=handoff_feature,
                    worktree=mock_worktree,
                )
            )

            mock_execute_task.assert_not_called()

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, TaskExecutionResult)
        assert result.task_id == "TASK-FPTC-OP1"
        assert result.final_decision == "deferred"
        # Terminal-but-not-failed: the wave does not fail because of this task.
        assert result.success is True
        assert result.deferred_reason == HANDOFF_REASON
        assert result.total_turns == 0
        assert result.error is None

    def test_handoff_skip_does_not_construct_autobuild_orchestrator(
        self, handoff_repo, handoff_feature, mock_worktree, mock_worktree_manager
    ):
        """Handoff skip burns no SDK budget — AutoBuildOrchestrator never made."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )

        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator"
        ) as mock_ab:
            asyncio.run(
                orchestrator._execute_wave_parallel(
                    wave_number=1,
                    task_ids=["TASK-FPTC-OP1"],
                    feature=handoff_feature,
                    worktree=mock_worktree,
                )
            )
            mock_ab.assert_not_called()


# ============================================================================
# AC-FPTC-003-02: deferred outcome distinct from BLOCKED/FAILED/COMPLETED
# ============================================================================


class TestDeferredOutcomeIsDistinct:
    """AC-FPTC-003-02: deferred is its own terminal outcome."""

    def test_feature_task_status_accepts_deferred(self):
        """The FeatureTask status Literal admits 'deferred' as a value."""
        # Pydantic v2 model_validate raises on bad Literal values, so this
        # is the structural pin that the new state exists.
        task = FeatureTask(
            id="TASK-FPTC-Z1",
            name="z",
            file_path=Path("tasks/backlog/TASK-FPTC-Z1.md"),
            status="deferred",
        )
        assert task.status == "deferred"

    def test_persisted_task_status_is_deferred_not_completed_or_failed(
        self, handoff_repo, handoff_feature, mock_worktree, mock_worktree_manager
    ):
        """After skip, feature.tasks[id].status == 'deferred', not completed/failed."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )
        asyncio.run(
            orchestrator._execute_wave_parallel(
                wave_number=1,
                task_ids=["TASK-FPTC-OP1"],
                feature=handoff_feature,
                worktree=mock_worktree,
            )
        )
        task = handoff_feature.tasks[0]
        assert task.status == "deferred"
        assert task.status not in ("completed", "failed", "blocked", "skipped")


# ============================================================================
# AC-FPTC-003-03: wave-summary surfaces deferred entry with title + reason
# ============================================================================


class TestWaveSummarySurface:
    """AC-FPTC-003-03: deferred entry surfaces task ID, title, reason."""

    def test_persisted_result_carries_deferred_reason_and_title_traceable(
        self, handoff_repo, handoff_feature, mock_worktree, mock_worktree_manager
    ):
        """task.result carries final_decision + deferred_reason; task.name is title."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )
        asyncio.run(
            orchestrator._execute_wave_parallel(
                wave_number=1,
                task_ids=["TASK-FPTC-OP1"],
                feature=handoff_feature,
                worktree=mock_worktree,
            )
        )
        task = handoff_feature.tasks[0]
        assert task.result is not None
        assert task.result["final_decision"] == "deferred"
        assert task.result["deferred_reason"] == HANDOFF_REASON
        # Title round-trips so /feature-complete (TASK-FPTC-005) can render
        # "task ID + title + reason" without re-loading the task file.
        assert task.name == "Rotate production credentials"

    def test_stdout_banner_surfaces_deferred_entry(
        self,
        handoff_repo,
        handoff_feature,
        mock_worktree,
        mock_worktree_manager,
        capsys,
    ):
        """Without a wave_display, stdout carries task_id + title + reason."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )
        # Force the no-wave_display path so the console.print branch fires.
        orchestrator._wave_display = None

        asyncio.run(
            orchestrator._execute_wave_parallel(
                wave_number=1,
                task_ids=["TASK-FPTC-OP1"],
                feature=handoff_feature,
                worktree=mock_worktree,
            )
        )
        # Rich console wraps long lines; collapse whitespace before matching.
        captured = capsys.readouterr()
        normalized = " ".join(captured.out.split())
        # AC-FPTC-003-03: task ID + title + reason all appear together.
        assert "TASK-FPTC-OP1" in normalized
        assert "Rotate production credentials" in normalized
        assert HANDOFF_REASON in normalized

    def test_wave_display_receives_deferred_status_update(
        self, handoff_repo, handoff_feature, mock_worktree, mock_worktree_manager
    ):
        """When a wave_display is wired, it receives a DEFERRED-labelled update."""
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )
        wave_display = MagicMock()
        orchestrator._wave_display = wave_display

        asyncio.run(
            orchestrator._execute_wave_parallel(
                wave_number=1,
                task_ids=["TASK-FPTC-OP1"],
                feature=handoff_feature,
                worktree=mock_worktree,
            )
        )

        # The skip branch fires update_task_status with the DEFERRED label
        # and reason in the details string.
        deferred_calls = [
            c for c in wave_display.update_task_status.call_args_list
            if "TASK-FPTC-OP1" in c.args
            and len(c.args) >= 3
            and "DEFERRED" in c.args[2]
        ]
        assert deferred_calls, (
            f"expected DEFERRED status update, got "
            f"{wave_display.update_task_status.call_args_list}"
        )
        assert HANDOFF_REASON in deferred_calls[0].args[2]


# ============================================================================
# Mixed-task wave: handoff coexists with normal feature task
# ============================================================================


class TestMixedWave:
    """A wave with one feature task + one operator_handoff dispatches one, defers one."""

    def test_only_feature_task_is_dispatched_handoff_is_deferred(
        self, mixed_repo, mixed_feature, mock_worktree, mock_worktree_manager
    ):
        """_execute_task is called once (for the feature task), not for the handoff."""
        orchestrator = FeatureOrchestrator(
            repo_root=mixed_repo,
            worktree_manager=mock_worktree_manager,
        )

        def fake_execute(task, *args, **kwargs):
            return TaskExecutionResult(
                task_id=task.id,
                success=True,
                total_turns=1,
                final_decision="approved",
            )

        with patch.object(
            orchestrator, "_execute_task", side_effect=fake_execute
        ) as mock_execute_task:
            results = asyncio.run(
                orchestrator._execute_wave_parallel(
                    wave_number=1,
                    task_ids=["TASK-FPTC-N1", "TASK-FPTC-H1"],
                    feature=mixed_feature,
                    worktree=mock_worktree,
                )
            )

        # _execute_task fired exactly once — for the normal task.
        assert mock_execute_task.call_count == 1
        dispatched_task = mock_execute_task.call_args.args[0]
        assert dispatched_task.id == "TASK-FPTC-N1"

        # The two outcomes match expectations.
        by_id = {r.task_id: r for r in results}
        assert by_id["TASK-FPTC-N1"].final_decision == "approved"
        assert by_id["TASK-FPTC-N1"].success is True
        assert by_id["TASK-FPTC-H1"].final_decision == "deferred"
        assert by_id["TASK-FPTC-H1"].success is True
        assert by_id["TASK-FPTC-H1"].deferred_reason == HANDOFF_REASON


# ============================================================================
# Helper: _read_task_type_from_frontmatter
# ============================================================================


class TestReadTaskTypeFromFrontmatter:
    """Helper resolves canonical task_type from frontmatter, with graceful fallback."""

    def test_resolves_operator_handoff(
        self, handoff_repo, mock_worktree_manager
    ):
        orchestrator = FeatureOrchestrator(
            repo_root=handoff_repo,
            worktree_manager=mock_worktree_manager,
        )
        assert (
            orchestrator._read_task_type_from_frontmatter("TASK-FPTC-OP1")
            == "operator_handoff"
        )

    def test_returns_none_when_task_file_missing(
        self, tmp_path, mock_worktree_manager
    ):
        """Missing task file → None (loader error caught, falls through to dispatch)."""
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
        )
        assert (
            orchestrator._read_task_type_from_frontmatter("TASK-DOES-NOT-EXIST")
            is None
        )

    def test_resolves_alias_to_canonical(
        self, tmp_path, mock_worktree_manager
    ):
        """Alias values normalise to the canonical TaskType string."""
        _write_task_md(
            tmp_path,
            "tasks/backlog/TASK-FPTC-AL1.md",
            "TASK-FPTC-AL1",
            "Alias case",
            "enhancement",  # alias for FEATURE
        )
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
        )
        assert (
            orchestrator._read_task_type_from_frontmatter("TASK-FPTC-AL1")
            == "feature"
        )
