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
