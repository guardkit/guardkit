"""Operator follow-up checklist surfaced in /feature-complete (TASK-FPTC-005).

Pins AC-FPTC-005-02 / -04 / -05: when one or more tasks were marked
``status: deferred`` by the orchestrator skip branch (TASK-FPTC-003),
``/feature-complete``'s merge summary must surface a "Required operator
follow-up" subsection containing each deferred task's ID, title, and the
runtime-shaped ACs verbatim from the task body. When zero tasks were
deferred, the subsection must not render at all (no empty headers).

Coverage Target: >=85%
"""

from __future__ import annotations

import io
from pathlib import Path
from textwrap import dedent
from typing import List
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from guardkit.orchestrator.feature_complete import (
    FeatureCompleteOrchestrator,
    _collect_deferred_tasks,
    _extract_operator_followup_acs,
    render_operator_followup_panel,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
)


# ============================================================================
# Fixtures
# ============================================================================


def _operator_handoff_body(
    task_id: str, title: str, ac_bullets: List[str]
) -> str:
    """Return a task md body that mirrors what /feature-plan emits.

    The "Required operator follow-up" template is owned by
    feature-plan.md; mirroring it here keeps the tests aligned with the
    cross-task contract the planner actually produces.
    """

    lines = [
        "---",
        f"id: {task_id}",
        f'title: "{title}"',
        "status: backlog",
        "task_type: operator_handoff",
        "---",
        "",
        f"# Task: {title}",
        "",
        "## Description",
        "",
        "Body.",
        "",
        "## Required operator follow-up",
        "",
        "This task is `task_type: operator_handoff` — AutoBuild will not "
        "attempt it. The operator must verify the runtime acceptance "
        "criteria below manually, then mark the task complete via "
        "`/task-complete`.",
        "",
    ]
    lines.extend(ac_bullets)
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Trailing bullet that must be ignored by the extractor.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_task_body(tmp_path: Path, rel_path: str, body: str) -> Path:
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body, encoding="utf-8")
    return full


def _make_feature_task(
    *,
    task_id: str,
    name: str,
    status: str,
    file_path: Path,
) -> FeatureTask:
    return FeatureTask(
        id=task_id,
        name=name,
        file_path=file_path,
        complexity=3,
        dependencies=[],
        status=status,
        implementation_mode="task-work",
        estimated_minutes=30,
    )


def _make_feature(tasks: List[FeatureTask]) -> Feature:
    execution = FeatureExecution(
        started_at=None,
        completed_at=None,
        worktree_path=None,
        current_wave=0,
        completed_waves=[],
        tasks_completed=len([t for t in tasks if t.status == "completed"]),
        tasks_failed=0,
        total_turns=0,
        last_updated=None,
    )
    orchestration = FeatureOrchestration(
        parallel_groups=[[t.id for t in tasks]],
        estimated_duration_minutes=60,
        recommended_parallel=1,
    )
    return Feature(
        id="FEAT-FPTC-005",
        name="Feature with deferred tasks",
        description="Fixture feature for the operator follow-up surface.",
        created="2026-05-03T15:00:00Z",
        status="in_progress",
        complexity=4,
        estimated_tasks=len(tasks),
        tasks=tasks,
        orchestration=orchestration,
        execution=execution,
    )


def _capture_panel_text(panel) -> str:
    buf = io.StringIO()
    Console(file=buf, force_terminal=False, width=200).print(panel)
    return buf.getvalue()


# ============================================================================
# 1. _extract_operator_followup_acs (4 tests)
# ============================================================================


class TestExtractOperatorFollowupAcs:
    """Bullet extraction from the Required-operator-follow-up section."""

    def test_extracts_bullets_verbatim(self, tmp_path: Path):
        body = _operator_handoff_body(
            "TASK-OP1",
            "Rotate creds",
            [
                "- **AC-OP1-01**: Run `kubectl rollout status` and "
                "confirm zero downtime.",
                "- **AC-OP1-02**: Tail Grafana panel `auth.errors` for "
                "10 minutes and confirm no spike.",
            ],
        )
        task_file = _write_task_body(tmp_path, "tasks/backlog/TASK-OP1.md", body)

        bullets = _extract_operator_followup_acs(task_file)

        assert bullets == [
            "- **AC-OP1-01**: Run `kubectl rollout status` and "
            "confirm zero downtime.",
            "- **AC-OP1-02**: Tail Grafana panel `auth.errors` for "
            "10 minutes and confirm no spike.",
        ]

    def test_returns_empty_when_section_missing(self, tmp_path: Path):
        body = dedent(
            """\
            ---
            id: TASK-OP2
            ---

            # Task: no follow-up section

            Just description, no operator block.
            """
        )
        task_file = _write_task_body(tmp_path, "tasks/backlog/TASK-OP2.md", body)

        assert _extract_operator_followup_acs(task_file) == []

    def test_returns_empty_when_file_missing(self, tmp_path: Path):
        missing = tmp_path / "tasks" / "backlog" / "TASK-NOPE.md"
        # Parent dir intentionally not created — the helper must tolerate
        # a stale FeatureTask.file_path without crashing the merge summary.
        assert _extract_operator_followup_acs(missing) == []

    def test_stops_at_next_top_level_heading(self, tmp_path: Path):
        body = _operator_handoff_body(
            "TASK-OP3",
            "Stop at next heading",
            ["- **AC-OP3-01**: Step in scope."],
        )
        task_file = _write_task_body(tmp_path, "tasks/backlog/TASK-OP3.md", body)

        bullets = _extract_operator_followup_acs(task_file)

        # The fixture body contains a trailing "## Notes" section with a
        # bullet that must NOT leak into the operator-followup output.
        assert bullets == ["- **AC-OP3-01**: Step in scope."]


# ============================================================================
# 2. _collect_deferred_tasks (3 tests)
# ============================================================================


class TestCollectDeferredTasks:
    """Pairing deferred FeatureTasks with their AC bullet lines."""

    def test_picks_only_deferred_tasks(self, tmp_path: Path):
        deferred_body = _operator_handoff_body(
            "TASK-DEF",
            "Deferred task",
            ["- **AC-DEF-01**: Manual step."],
        )
        deferred_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-DEF.md", deferred_body
        )
        completed_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-DONE.md", "stub"
        )

        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-DONE",
                    name="Done task",
                    status="completed",
                    file_path=completed_file.relative_to(tmp_path),
                ),
                _make_feature_task(
                    task_id="TASK-DEF",
                    name="Deferred task",
                    status="deferred",
                    file_path=deferred_file.relative_to(tmp_path),
                ),
            ]
        )

        pairs = _collect_deferred_tasks(feature, tmp_path)

        assert [task.id for task, _ in pairs] == ["TASK-DEF"]
        assert pairs[0][1] == ["- **AC-DEF-01**: Manual step."]

    def test_returns_empty_when_no_deferred_tasks(self, tmp_path: Path):
        completed_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-OK.md", "stub"
        )
        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-OK",
                    name="Completed task",
                    status="completed",
                    file_path=completed_file.relative_to(tmp_path),
                )
            ]
        )

        assert _collect_deferred_tasks(feature, tmp_path) == []

    def test_resolves_relative_file_paths_against_repo_root(
        self, tmp_path: Path
    ):
        body = _operator_handoff_body(
            "TASK-REL",
            "Relative path task",
            ["- **AC-REL-01**: Step under relative path."],
        )
        rel_path = Path("tasks/backlog/TASK-REL.md")
        _write_task_body(tmp_path, str(rel_path), body)

        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-REL",
                    name="Relative path task",
                    status="deferred",
                    file_path=rel_path,  # repo-relative, not absolute
                )
            ]
        )

        pairs = _collect_deferred_tasks(feature, tmp_path)

        assert pairs[0][1] == ["- **AC-REL-01**: Step under relative path."]


# ============================================================================
# 3. render_operator_followup_panel (4 tests, covers AC-FPTC-005-02/04/05)
# ============================================================================


class TestRenderOperatorFollowupPanel:
    """Merge-summary checklist rendering."""

    def test_two_deferred_tasks_show_both_ids_titles_and_acs(
        self, tmp_path: Path
    ):
        """AC-FPTC-005-04: 2 deferred tasks → both IDs and titles in section."""
        body_a = _operator_handoff_body(
            "TASK-OP-A",
            "Rotate prod credentials",
            [
                "- **AC-OPA-01**: Confirm `kubectl rollout status` exits 0.",
                "- **AC-OPA-02**: Watch Grafana for 10 minutes.",
            ],
        )
        body_b = _operator_handoff_body(
            "TASK-OP-B",
            "Run live MCP tutor session",
            ["- **AC-OPB-01**: Walk a tutor session via Claude Desktop."],
        )
        file_a = _write_task_body(tmp_path, "tasks/backlog/TASK-OP-A.md", body_a)
        file_b = _write_task_body(tmp_path, "tasks/backlog/TASK-OP-B.md", body_b)
        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-OP-A",
                    name="Rotate prod credentials",
                    status="deferred",
                    file_path=file_a.relative_to(tmp_path),
                ),
                _make_feature_task(
                    task_id="TASK-OP-B",
                    name="Run live MCP tutor session",
                    status="deferred",
                    file_path=file_b.relative_to(tmp_path),
                ),
            ]
        )

        deferred = _collect_deferred_tasks(feature, tmp_path)
        panel = render_operator_followup_panel(deferred)
        rendered = _capture_panel_text(panel)

        # AC-FPTC-005-02: section title present.
        assert "Required operator follow-up" in rendered
        # Both task IDs and titles are present.
        assert "TASK-OP-A" in rendered
        assert "Rotate prod credentials" in rendered
        assert "TASK-OP-B" in rendered
        assert "Run live MCP tutor session" in rendered
        # AC bullets carry through verbatim.
        assert "AC-OPA-01" in rendered
        assert "kubectl rollout status" in rendered
        assert "AC-OPA-02" in rendered
        assert "AC-OPB-01" in rendered

    def test_zero_deferred_tasks_returns_none(self):
        """AC-FPTC-005-05: 0 deferred tasks → no operator-follow-up subsection."""
        assert render_operator_followup_panel([]) is None

    def test_handles_missing_ac_section_gracefully(self, tmp_path: Path):
        # Task body has no operator follow-up section; the panel should
        # still render the task entry with a clear placeholder rather
        # than crashing or silently omitting it.
        empty_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-OPC.md", "no follow-up section"
        )
        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-OPC",
                    name="Missing template",
                    status="deferred",
                    file_path=empty_file.relative_to(tmp_path),
                )
            ]
        )

        deferred = _collect_deferred_tasks(feature, tmp_path)
        panel = render_operator_followup_panel(deferred)
        rendered = _capture_panel_text(panel)

        assert "TASK-OPC" in rendered
        assert "Missing template" in rendered
        assert "No runtime ACs" in rendered

    def test_orchestrator_handoff_phase_emits_panel(
        self, tmp_path: Path, capsys
    ):
        """Integration: _handoff_phase prints the panel via console.

        Exercises the full ``_handoff_phase → _display_operator_followup``
        path so a regression in either helper or the wiring is caught.
        """

        body = _operator_handoff_body(
            "TASK-INT",
            "Integration deferred task",
            ["- **AC-INT-01**: Manual integration check."],
        )
        task_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-INT.md", body
        )
        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-INT",
                    name="Integration deferred task",
                    status="deferred",
                    file_path=task_file.relative_to(tmp_path),
                )
            ]
        )

        # Build orchestrator without invoking WorktreeManager (which
        # requires real git plumbing).
        orchestrator = FeatureCompleteOrchestrator.__new__(
            FeatureCompleteOrchestrator
        )
        orchestrator.repo_root = tmp_path
        orchestrator.dry_run = False
        orchestrator.force = False
        orchestrator._worktree_manager = MagicMock()

        orchestrator._handoff_phase(feature, worktree=None)

        captured = capsys.readouterr().out
        assert "Required operator follow-up" in captured
        assert "TASK-INT" in captured
        assert "AC-INT-01" in captured


# ============================================================================
# 4. AC-FPTC-005-05 — empty-feature regression guard at orchestrator level
# ============================================================================


class TestOrchestratorSuppressesEmptySection:
    """No deferred tasks → orchestrator must not print the section at all."""

    def test_handoff_phase_omits_section_when_no_deferred(
        self, tmp_path: Path, capsys
    ):
        completed_file = _write_task_body(
            tmp_path, "tasks/backlog/TASK-OK.md", "stub"
        )
        feature = _make_feature(
            [
                _make_feature_task(
                    task_id="TASK-OK",
                    name="Completed task",
                    status="completed",
                    file_path=completed_file.relative_to(tmp_path),
                )
            ]
        )
        orchestrator = FeatureCompleteOrchestrator.__new__(
            FeatureCompleteOrchestrator
        )
        orchestrator.repo_root = tmp_path
        orchestrator.dry_run = False
        orchestrator.force = False
        orchestrator._worktree_manager = MagicMock()

        orchestrator._handoff_phase(feature, worktree=None)

        captured = capsys.readouterr().out
        assert "Required operator follow-up" not in captured
