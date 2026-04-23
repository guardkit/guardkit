"""
Phase 5.5 (Plan Audit) execution helpers.

Entry point imported by ``guardkit.orchestrator.agent_invoker`` on the
autobuild producer path (see TASK-FIX-RWOP1.3.2). The interactive
``handle_audit_decision`` path is retained for the manual ``/task-work``
workflow.

Prior iterations of this module also housed ``execute_phases`` /
``execute_design_phases`` / ``execute_implementation_phases`` and a
Phase 1.6 clarification runner. None of those had runtime callers —
they were aspirational drivers for a never-wired ``--design-only`` /
``--implement-only`` flow — and were removed in TASK-FIX-RWOP1.3.3.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import glob as glob_module
import logging

logger = logging.getLogger(__name__)


class PhaseExecutionError(Exception):
    """Raised when phase execution fails."""
    pass


def _plan_exists(task_id: str, workspace_root: Optional[Path] = None) -> bool:
    """Check whether an implementation plan is on disk for ``task_id``.

    Looks under ``{workspace_root or cwd}/docs/state/{task_id}/`` for
    ``implementation_plan.md`` (preferred) or ``.json`` (legacy).
    """
    root = workspace_root if workspace_root is not None else Path(".")
    state_dir = root / "docs" / "state" / task_id
    return (state_dir / "implementation_plan.md").exists() or (
        state_dir / "implementation_plan.json"
    ).exists()


def execute_phase_5_5_plan_audit(
    task_id: str,
    task_context: Dict[str, Any],
    non_interactive: bool = False,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Phase 5.5: Audit implementation against saved plan.

    Implements Hubbard's Step 6 (Audit) — verifies that actual
    implementation matches the approved architectural plan.

    Args:
        task_id: Task identifier.
        task_context: Task context from the task file (unused today; kept
            in the signature because autobuild's producer passes it).
        non_interactive: When True, run the auditor without prompting,
            without printing the report, and without mutating task
            metadata or creating follow-up tasks. Use this from the
            autobuild producer path
            (``AgentInvoker._write_task_work_results``) where the Player
            must not be asked for a decision and Coach consumes the
            returned report via ``task_work_results.plan_audit``.
            Default: False (historical interactive /task-work behaviour).
        workspace_root: Optional workspace root for plan lookup and file
            scanning. When None, uses the current working directory.
            AgentInvoker passes ``self.worktree_path`` so the audit
            resolves plans from the right worktree even when the
            orchestrator's cwd differs. Default: None.

    Returns:
        Dictionary with audit results::

            {
                "approved": bool,
                "report": PlanAuditReport | None,
                "decision": str,
                "skipped": bool,
                "error": str  # only present on auditor failure
            }

        The non-interactive path derives ``approved`` from severity:
        ``severity == "high"`` → False, else True. The ``decision`` is
        ``"non_interactive"`` on success, ``"skipped"`` when no plan
        exists, and ``"error"`` when the auditor raised.
    """
    from .plan_audit import PlanAuditor, format_audit_report, PlanAuditError
    from .metrics.plan_audit_metrics import PlanAuditMetricsTracker

    # Check if plan exists
    if not _plan_exists(task_id, workspace_root):
        if not non_interactive:
            print("⚠️  No implementation plan found - skipping audit")
        return {"approved": True, "report": None, "decision": "skipped", "skipped": True}

    try:
        # Run audit (workspace-rooted when provided so the auditor scans
        # the worktree, not the orchestrator's cwd).
        auditor = PlanAuditor(workspace_root=workspace_root or Path("."))
        report = auditor.audit_implementation(task_id)

        if non_interactive:
            # Producer path: return the raw audit report without the
            # interactive prompt, stdout dump, task-metadata mutation,
            # or follow-up task creation. All of those are UX affordances
            # for the manual /task-work flow; autobuild Coach only needs
            # the deterministic verdict. Metrics are also skipped here —
            # the interactive handler owns metric recording so we don't
            # double-count every producer write.
            approved = report.severity != "high"
            return {
                "approved": approved,
                "report": report,
                "decision": "non_interactive",
                "skipped": False,
            }

        # Display report
        print("\n" + format_audit_report(report))

        # Prompt for decision with timeout
        decision = prompt_with_timeout(
            "Choice [A]pprove/[R]evise/[E]scalate/[C]ancel (30s timeout = auto-approve): ",
            timeout=30,
            default="A"
        )

        # Handle decision
        approved = handle_audit_decision(task_id, report, decision)

        # Track metrics
        tracker = PlanAuditMetricsTracker()
        tracker.record_audit(task_id, report, decision.lower())

        return {
            "approved": approved,
            "report": report,
            "decision": decision.lower(),
            "skipped": False
        }

    except PlanAuditError as e:
        if non_interactive:
            return {
                "approved": True,
                "report": None,
                "decision": "error",
                "skipped": False,
                "error": str(e),
            }
        print(f"⚠️  Audit error: {e}")
        print("Defaulting to approve (non-blocking)")
        return {"approved": True, "report": None, "decision": "error", "skipped": False}


def prompt_with_timeout(prompt: str, timeout: int, default: str) -> str:
    """Prompt user with timeout; auto-returns ``default`` after timeout.

    Uses a daemon thread so a pending ``input()`` never blocks shutdown
    if the timeout fires.
    """
    import threading

    result = [default]

    def get_input():
        try:
            result[0] = input(prompt).strip().upper()
        except Exception:
            pass

    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print(f"\n⏱️  Timeout - defaulting to [{default}]")

    return result[0]


def handle_audit_decision(
    task_id: str,
    report: Any,  # PlanAuditReport
    decision: str,
) -> bool:
    """Handle an interactive audit decision and update task state.

    Returns True when the task may proceed to IN_REVIEW, False when it
    should transition to BLOCKED.
    """
    decision_lower = decision.lower()

    if decision_lower == "a":
        print("✅ Audit approved - proceeding to IN_REVIEW")
        _update_task_metadata(task_id, report, "approved")
        return True

    if decision_lower == "r":
        print("❌ Audit revision requested - transitioning to BLOCKED")
        _update_task_metadata(task_id, report, "revision_requested")
        return False

    if decision_lower == "e":
        print("⚠️  Audit escalated - creating follow-up task")
        _create_followup_task(task_id, report)
        _update_task_metadata(task_id, report, "escalated")
        return True

    if decision_lower == "c":
        print("❌ Audit cancelled - transitioning to BLOCKED")
        _update_task_metadata(task_id, report, "cancelled")
        return False

    # Invalid input - default to approve with warning
    print(f"⚠️  Invalid input '{decision}' - defaulting to Approve")
    _update_task_metadata(task_id, report, "approved_default")
    return True


def _update_task_metadata(task_id: str, report: Any, decision: str) -> None:
    """Update task frontmatter with audit results."""
    task_file = _find_task_file(task_id)
    if not task_file:
        return

    try:
        from .task_utils import update_task_frontmatter

        update_task_frontmatter(
            task_file,
            {
                "plan_audit": {
                    "severity": report.severity,
                    "discrepancies_count": len(report.discrepancies),
                    "decision": decision,
                    "audited_at": report.timestamp,
                }
            },
            preserve_body=True,
        )
    except Exception as e:
        print(f"⚠️  Could not update task metadata: {e}")


def _create_followup_task(task_id: str, report: Any) -> None:
    """Record a follow-up task for scope-creep investigation."""
    # Placeholder - actual implementation would:
    # 1. Generate new task file in tasks/backlog/
    # 2. Link to original task
    # 3. Add discrepancies as requirements
    print(f"📝 Follow-up task created: {task_id}-AUDIT-FOLLOWUP")
    print("   (Note: Follow-up task creation not yet implemented)")


def _find_task_file(task_id: str) -> Optional[Path]:
    """Find a task file across state directories.

    Supports both exact filenames (``TASK-001.md``) and descriptive
    filenames (``TASK-001-add-feature.md``) via glob, and also looks one
    level deeper for feature folders (``tasks/backlog/feature-slug/``).
    """
    search_patterns = [
        "tasks/{state_dir}/{task_id}.md",            # Exact match
        "tasks/{state_dir}/{task_id}-*.md",          # With descriptor
        "tasks/{state_dir}/*/{task_id}.md",          # In feature folder
        "tasks/{state_dir}/*/{task_id}-*.md",        # In feature folder w/ descriptor
    ]

    state_dirs = ["in_progress", "backlog", "blocked", "in_review", "completed"]

    for state_dir in state_dirs:
        for pattern_template in search_patterns:
            pattern = pattern_template.format(state_dir=state_dir, task_id=task_id)
            matches = list(glob_module.glob(pattern))
            if matches:
                return Path(matches[0])

    return None


__all__ = [
    "execute_phase_5_5_plan_audit",
    "prompt_with_timeout",
    "handle_audit_decision",
    "PhaseExecutionError",
]
