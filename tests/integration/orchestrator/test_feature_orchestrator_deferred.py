"""End-to-end deferred-task integration test (TASK-FPTC-003 AC-FPTC-003-05).

Pins AC-FPTC-003-05: a fixture feature with one ``feature`` task and one
``operator_handoff`` task. The ``feature`` task runs through the
Player↔Coach mock loop, the ``operator_handoff`` task is reported as
deferred, and the run returns success (not failure).

Approach
--------
- Build a real on-disk repo with a feature YAML and two task markdown files.
- Stub ``WorktreeManager`` so no real git worktree is created.
- Stub ``AutoBuildOrchestrator`` to return a successful OrchestrationResult
  for the feature task — this stands in for the Player↔Coach mock loop
  without requiring any SDK calls.
- Drive the full ``FeatureOrchestrator.orchestrate`` lifecycle and assert
  on the resulting state.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrationResult,
    FeatureOrchestrator,
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
    """Write a minimal task markdown file with the given task_type."""
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
            complexity: 3
            ---

            # Task: {title}

            Body.

            ## Acceptance Criteria

            - [ ] AC-{task_id}-01 — Placeholder.
            """
        )
    )
    return task_file


@pytest.fixture
def integration_repo(tmp_path: Path) -> Path:
    """Build a repo with a feature YAML + one feature task + one operator_handoff."""
    repo_root = tmp_path

    feature = Feature(
        id="FEAT-FPTC-DEF",
        name="Deferred Integration Feature",
        description="One feature task + one operator_handoff (TASK-FPTC-003 AC-05)",
        created="2026-05-03T12:00:00Z",
        status="planned",
        complexity=4,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-FPTC-INT-N1",
                name="Normal feature task",
                file_path=Path("tasks/backlog/TASK-FPTC-INT-N1.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-FPTC-INT-H1",
                name="Hand off to operator",
                file_path=Path("tasks/backlog/TASK-FPTC-INT-H1.md"),
                complexity=2,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=10,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-FPTC-INT-N1", "TASK-FPTC-INT-H1"]],
            estimated_duration_minutes=40,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(),
    )

    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "FEAT-FPTC-DEF.yaml").write_text(
        yaml.dump(FeatureLoader._feature_to_dict(feature))
    )

    _write_task_md(
        repo_root,
        "tasks/backlog/TASK-FPTC-INT-N1.md",
        "TASK-FPTC-INT-N1",
        "Normal feature task",
        "feature",
    )
    _write_task_md(
        repo_root,
        "tasks/backlog/TASK-FPTC-INT-H1.md",
        "TASK-FPTC-INT-H1",
        "Hand off to operator",
        "operator_handoff",
    )

    return repo_root


@pytest.fixture
def stub_worktree(tmp_path: Path) -> Worktree:
    """Stub Worktree backed by a real (empty) directory."""
    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-FPTC-DEF"
    worktree_path.mkdir(parents=True, exist_ok=True)
    return Worktree(
        task_id="FEAT-FPTC-DEF",
        branch_name="autobuild/FEAT-FPTC-DEF",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def stub_worktree_manager(tmp_path: Path, stub_worktree: Worktree):
    """Stub WorktreeManager that returns the stub worktree without git ops."""
    manager = MagicMock()
    manager.create.return_value = stub_worktree
    manager.cleanup.return_value = None
    manager.preserve_on_failure.return_value = None
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    manager.worktrees_dir = worktrees_dir
    return manager


# ============================================================================
# AC-FPTC-003-05: end-to-end mixed-task feature run
# ============================================================================


def test_mixed_feature_run_defers_handoff_and_succeeds(
    integration_repo: Path, stub_worktree_manager
) -> None:
    """AC-FPTC-003-05: feature task runs, handoff defers, run returns success.

    The FeatureOrchestrator.orchestrate() lifecycle is driven end-to-end
    against a real on-disk repo. AutoBuildOrchestrator is stubbed to
    simulate a successful Player↔Coach loop for the feature task. The
    operator_handoff task must be reported as deferred without ever
    constructing the AutoBuildOrchestrator.
    """
    orchestrator = FeatureOrchestrator(
        repo_root=integration_repo,
        worktree_manager=stub_worktree_manager,
        max_turns=3,
        stop_on_failure=False,
    )

    # Mock AutoBuildOrchestrator so the Player↔Coach loop "succeeds" for
    # the normal feature task without any real SDK calls. The handoff
    # path must NOT route through this — that's enforced by the assertion
    # that this stub is called exactly once and only for the feature task.
    def fake_orchestrate(self, *, task_id, **kwargs):  # noqa: D401
        result = MagicMock()
        result.success = True
        result.total_turns = 1
        result.final_decision = "approved"
        result.error = None
        result.recovery_count = 0
        result.turn_history = []
        result.stall_classification = None
        return result

    fake_ab_class = MagicMock()
    fake_ab_class.side_effect = lambda **kwargs: MagicMock(
        orchestrate=lambda **call_kwargs: _fake_orchestrate_result(call_kwargs)
    )

    # Track which task IDs the AutoBuildOrchestrator was constructed for.
    constructed_for: list[str] = []

    def _ab_factory(**ctor_kwargs):
        ab_instance = MagicMock()

        def _orchestrate(**call_kwargs):
            constructed_for.append(call_kwargs.get("task_id"))
            return _fake_orchestrate_result(call_kwargs)

        ab_instance.orchestrate = _orchestrate
        return ab_instance

    with patch(
        "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
        side_effect=_ab_factory,
    ):
        result: FeatureOrchestrationResult = orchestrator.orchestrate(
            "FEAT-FPTC-DEF", base_branch="main"
        )

    # AC-FPTC-003-05: handoff was NOT dispatched into the Player↔Coach loop.
    assert constructed_for == ["TASK-FPTC-INT-N1"], (
        f"AutoBuildOrchestrator should be constructed exactly once "
        f"(for the feature task), got: {constructed_for}"
    )

    # AC-FPTC-003-05: the run returns success (not failure).
    assert result.success is True
    assert result.status == "completed"
    assert result.error is None

    # The two outcomes are reflected in the wave results.
    flat_results = [r for w in result.wave_results for r in w.results]
    by_id = {r.task_id: r for r in flat_results}

    assert by_id["TASK-FPTC-INT-N1"].final_decision == "approved"
    assert by_id["TASK-FPTC-INT-N1"].success is True

    # AC-FPTC-003-02 + 03: deferred outcome is terminal-but-not-failed,
    # carries the canonical reason string.
    handoff = by_id["TASK-FPTC-INT-H1"]
    assert handoff.final_decision == "deferred"
    assert handoff.success is True
    assert handoff.deferred_reason == HANDOFF_REASON
    assert handoff.total_turns == 0

    # The persisted feature reflects the deferred status, distinct from
    # completed/failed/skipped.
    feature = FeatureLoader.load_feature("FEAT-FPTC-DEF", integration_repo)
    statuses = {t.id: t.status for t in feature.tasks}
    assert statuses["TASK-FPTC-INT-N1"] == "completed"
    assert statuses["TASK-FPTC-INT-H1"] == "deferred"


def _fake_orchestrate_result(call_kwargs):
    """Return a stand-in OrchestrationResult mock for the feature task."""
    result = MagicMock()
    result.success = True
    result.total_turns = 1
    result.final_decision = "approved"
    result.error = None
    result.recovery_count = 0
    result.turn_history = []
    result.stall_classification = None
    return result
