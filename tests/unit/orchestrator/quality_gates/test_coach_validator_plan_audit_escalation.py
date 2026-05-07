"""AC-005 tests: plan-audit ``skipped`` escalation when AC names missing files.

Background: ``AgentInvoker._compute_plan_audit_verdict`` returns
``status: "skipped"`` whenever no implementation plan exists on disk —
which is the normal case for tasks not run through the design-phase
pipeline. The Coach gate then treats ``status: "skipped"`` as passing.

This is a corruption path: a Player can claim "AC-001: src/missing.py
exists" with status="complete", and the Coach gate sees no plan to
compare against → passes. AC-005 closes that gap by escalating
``skipped`` to ``violation`` (severity ``high``) when the AC text names
a file path that doesn't exist on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.agent_invoker import AgentInvoker


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


def _write_task_file(
    worktree: Path, task_id: str, acceptance_criteria_md: str
) -> Path:
    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.md"
    task_file.write_text(
        "---\n"
        f"id: {task_id}\n"
        "title: dummy\n"
        "status: in_progress\n"
        "task_type: feature\n"
        "---\n"
        "\n"
        "## Acceptance criteria\n"
        f"{acceptance_criteria_md}\n"
    )
    return task_file


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_ac005_skipped_with_missing_ac_path_escalates_to_violation(
    mock_audit, tmp_worktree: Path
):
    """AC-005: plan_audit skipped + AC names missing file → status='violation'."""
    mock_audit.return_value = {"skipped": True}

    _write_task_file(
        tmp_worktree,
        "TASK-001",
        "- [ ] AC-001: implement src/repro/missing.py",
    )

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["status"] == "violation"
    assert verdict["severity"] == "high"
    assert verdict["violations"] >= 1
    assert "src/repro/missing.py" in verdict["missing_files"]


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_ac005_skipped_with_existing_ac_path_stays_skipped(
    mock_audit, tmp_worktree: Path
):
    """AC-005: plan_audit skipped + AC names existing file → status remains 'skipped'."""
    mock_audit.return_value = {"skipped": True}

    target = tmp_worktree / "src" / "real.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# real")

    _write_task_file(
        tmp_worktree,
        "TASK-001",
        "- [ ] AC-001: implement src/real.py",
    )

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["status"] == "skipped"
    assert verdict["severity"] is None
    assert verdict["violations"] == 0


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_ac005_skipped_with_no_paths_in_ac_stays_skipped(
    mock_audit, tmp_worktree: Path
):
    """AC-005: plan_audit skipped + AC text mentions no file paths → stays 'skipped'."""
    mock_audit.return_value = {"skipped": True}

    _write_task_file(
        tmp_worktree,
        "TASK-001",
        "- [ ] AC-001: ensure helpful logging on error",
    )

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["status"] == "skipped"


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_ac005_backtick_quoted_paths_detected(
    mock_audit, tmp_worktree: Path
):
    """AC-005: backtick-quoted paths in AC text are detected (synthetic_report parity)."""
    mock_audit.return_value = {"skipped": True}

    _write_task_file(
        tmp_worktree,
        "TASK-001",
        "- [ ] AC-001: implement `src/auth/login.py`",
    )

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["status"] == "violation"
    assert "src/auth/login.py" in verdict["missing_files"]


# ============================================================================
# TASK-GK-PA-001 regression: discrepancy → verdict-field routing
# ----------------------------------------------------------------------------
# The producer's discriminator for ``extra_modifications`` was
# ``disc.message.startswith("unplanned modification")``, but the actual
# ``plan_audit.py`` producer emits ``f"{N} unplanned modification(s)"`` —
# always digit-prefixed. The ``startswith`` check never matched, so the
# ``extra_modifications`` field was structurally always ``[]`` even when
# the auditor had detected unplanned modifications.
#
# These tests construct a real ``PlanAuditReport`` containing the exact
# message the producer emits and assert that ``_compute_plan_audit_verdict``
# routes ``extra_modifications`` and ``missing_modifications`` correctly.
# Pre-existing tests bypassed this loop by hand-crafting the verdict dict
# directly into ``task_work_results`` — they passed despite the bug.
# ============================================================================


def _make_audit_result(discrepancies: list, severity: str = "medium") -> dict:
    """Build a ``execute_phase_5_5_plan_audit`` return value containing a
    real ``PlanAuditReport`` with the supplied discrepancies."""
    from installer.core.commands.lib.plan_audit import PlanAuditReport

    report = PlanAuditReport(
        task_id="TASK-001",
        plan_summary={},
        actual_summary={},
        discrepancies=discrepancies,
        severity=severity,
        recommendations=[],
        timestamp="2026-05-07T00:00:00Z",
        plan_path="docs/state/TASK-001/implementation_plan.json",
        audit_duration_seconds=0.01,
    )
    return {"decision": "ok", "report": report}


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_taskgkpa001_extra_modifications_routed_from_digit_prefixed_message(
    mock_audit, tmp_worktree: Path
):
    """Regression: ``"2 unplanned modification(s)"`` discrepancy → verdict
    ``extra_modifications == ["x.py", "y.py"]``.

    Pre-fix, the producer's ``startswith("unplanned modification")``
    check never matched the digit-prefixed producer message and
    ``extra_modifications`` was always ``[]`` — silently dropping the
    auditor's signal before Coach saw it.
    """
    from installer.core.commands.lib.plan_audit import Discrepancy

    disc = Discrepancy(
        category="files",
        severity="medium",
        message="2 unplanned modification(s)",
        planned=["a.py"],
        actual=["x.py", "y.py"],
        variance=200.0,
    )
    mock_audit.return_value = _make_audit_result([disc], severity="medium")

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["extra_modifications"] == ["x.py", "y.py"], (
        "discriminator must route digit-prefixed "
        "'unplanned modification(s)' message to extra_modifications"
    )
    # Sanity: it must not also leak into the creation-axis field.
    assert verdict["extra_files"] == []


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_taskgkpa001_missing_modifications_routed_from_planned_not_modified_message(
    mock_audit, tmp_worktree: Path
):
    """Mirror: ``"3 planned file(s) not modified"`` discrepancy → verdict
    ``missing_modifications == disc.planned``.

    The companion ``"not modified" in disc.message`` discriminator works
    correctly (substring match, not ``startswith``); this test pins that
    behavior so a future refactor can't break it.
    """
    from installer.core.commands.lib.plan_audit import Discrepancy

    planned = ["a.py", "b.py", "c.py"]
    disc = Discrepancy(
        category="files",
        severity="medium",
        message="3 planned file(s) not modified",
        planned=planned,
        actual=[],
        variance=100.0,
    )
    mock_audit.return_value = _make_audit_result([disc], severity="medium")

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["missing_modifications"] == planned, (
        "discriminator must route 'planned file(s) not modified' message "
        "to missing_modifications"
    )
    # The "not modified" message must not be misrouted into
    # missing_files (which uses the "missing"/"not created" discriminator).
    assert verdict["missing_files"] == []


@patch("guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit")
def test_taskgkpa001_modify_axis_does_not_collide_with_extra_files(
    mock_audit, tmp_worktree: Path
):
    """Order safety: a single report with both an unplanned-modification
    discrepancy and an extra-files discrepancy must populate both verdict
    fields without cross-contamination.

    Pins the elif ordering: modify-axis branches run BEFORE the generic
    ``"extra" in disc.message`` branch, so the modify message can't be
    miscategorised even if a future producer message phrasing happens
    to contain ``"extra"`` as a substring.
    """
    from installer.core.commands.lib.plan_audit import Discrepancy

    extra_modify_disc = Discrepancy(
        category="files",
        severity="medium",
        message="1 unplanned modification(s)",
        planned=[],
        actual=["modified_unexpectedly.py"],
        variance=100.0,
    )
    extra_files_disc = Discrepancy(
        category="files",
        severity="high",
        message="3 extra file(s) not in plan",
        planned=[],
        actual=["e1.py", "e2.py", "e3.py"],
        variance=300.0,
    )
    mock_audit.return_value = _make_audit_result(
        [extra_modify_disc, extra_files_disc], severity="high"
    )

    invoker = AgentInvoker(worktree_path=tmp_worktree)
    verdict = invoker._compute_plan_audit_verdict("TASK-001")

    assert verdict["extra_modifications"] == ["modified_unexpectedly.py"]
    assert verdict["extra_files"] == ["e1.py", "e2.py", "e3.py"]
