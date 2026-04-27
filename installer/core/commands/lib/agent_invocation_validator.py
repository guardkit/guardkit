"""
Agent Invocation Validator for task-work execution validation.

This module provides validation for agent invocations to ensure that all
required agents were actually invoked during task-work execution before
generating completion reports.

This prevents false reporting where agents are listed as "used" when they
were never called via the Task tool.

Task Reference: TASK-ENF1
Epic: agent-invocation-enforcement
Related: TASK-8D3F (identified gap), TASK-ENF2 (tracking implementation)
"""

from typing import List, Dict, Any, Optional

try:
    from .agent_invocation_tracker import AgentInvocationTracker
except ImportError:
    from agent_invocation_tracker import AgentInvocationTracker


# Task-type strings that resolve to TaskType.DECLARATIVE — declarative tasks
# (Pydantic models, DTOs, settings, constants) have no meaningful Phase-3
# stack-specific specialist to invoke; the schema *is* the implementation.
# Mirrors guardkit.models.task_types.TASK_TYPE_ALIASES — keep in sync if more
# aliases mapping to TaskType.DECLARATIVE are added there. (TASK-ABSR-1357)
_DECLARATIVE_TASK_TYPES = frozenset({"declarative", "config", "dto"})


def _is_declarative(task_type: Optional[str]) -> bool:
    """True if ``task_type`` resolves to TaskType.DECLARATIVE (or alias).

    Returns False for None and unknown values so the validator silently
    no-ops — declarative-suppression must never accidentally relax a real
    task_type's expectations.
    """
    if not task_type:
        return False
    return task_type in _DECLARATIVE_TASK_TYPES


class ValidationError(Exception):
    """Raised when agent invocation validation fails."""
    pass


def get_expected_phases(
    workflow_mode: str,
    task_type: Optional[str] = None,
) -> int:
    """
    Get expected number of agent invocations based on workflow mode.

    Standard: 5 phases (Planning, Arch Review, Implementation, Testing, Code Review)
    Micro: 3 phases (Planning, Implementation, Quick Review)
    Design-only: 3 phases (Planning, Arch Review, Complexity)
    Implement-only: 3 phases (Implementation, Testing, Code Review)
        — but 2 phases (Testing, Code Review) when ``task_type`` is
        declarative (TASK-ABSR-1357): declarative tasks have no Phase-3
        stack-specific specialist to invoke, so requiring one produces a
        non-actionable advisory.
    Direct: 1 phase (Implementation only — direct-mode tasks bypass
        task-work delegation; Phase 4/5 are owned by the orchestrator
        when wired, otherwise relaxed per ``_write_direct_mode_results``).

    Args:
        workflow_mode: One of 'standard', 'micro', 'design-only',
            'implement-only', 'direct'
        task_type: Optional task_type string from the task frontmatter
            (e.g. 'feature', 'declarative', 'config'). Aliases ('config',
            'dto') are resolved to 'declarative'. When None, behaves as
            today — preserves backward-compat for all existing call sites.

    Returns:
        Expected number of agent invocations for the workflow mode

    Examples:
        >>> get_expected_phases('standard')
        5
        >>> get_expected_phases('micro')
        3
        >>> get_expected_phases('design-only')
        3
        >>> get_expected_phases('direct')
        1
        >>> get_expected_phases('unknown')
        5
        >>> get_expected_phases('implement-only', task_type='declarative')
        2
        >>> get_expected_phases('implement-only', task_type='config')
        2
        >>> get_expected_phases('implement-only', task_type='feature')
        3
    """
    if workflow_mode == "implement-only" and _is_declarative(task_type):
        return 2

    phase_counts = {
        "standard": 5,
        "micro": 3,
        "design-only": 3,
        "implement-only": 3,
        "direct": 1,
    }
    return phase_counts.get(workflow_mode, 5)


def get_expected_phase_list(
    workflow_mode: str,
    task_type: Optional[str] = None,
) -> List[str]:
    """
    Get list of expected phase identifiers for a workflow mode.

    Args:
        workflow_mode: One of 'standard', 'micro', 'design-only',
            'implement-only', 'direct'
        task_type: Optional task_type string. When ``workflow_mode ==
            "implement-only"`` AND ``task_type`` is declarative (or an
            alias: 'config', 'dto'), Phase 3 is omitted — declarative
            tasks have no stack-specific Phase-3 specialist to invoke
            (TASK-ABSR-1357).

    Returns:
        List of phase identifiers expected for this workflow mode

    Examples:
        >>> get_expected_phase_list('standard')
        ['2', '2.5B', '3', '4', '5']
        >>> get_expected_phase_list('micro')
        ['3', '4', '5']
        >>> get_expected_phase_list('direct')
        ['3']
        >>> get_expected_phase_list('implement-only', task_type='declarative')
        ['4', '5']
        >>> get_expected_phase_list('implement-only', task_type='dto')
        ['4', '5']
    """
    if workflow_mode == "implement-only" and _is_declarative(task_type):
        return ['4', '5']

    phase_lists = {
        "standard": ['2', '2.5B', '3', '4', '5'],
        "micro": ['3', '4', '5'],
        "design-only": ['2', '2.5B', '2.7'],
        "implement-only": ['3', '4', '5'],
        "direct": ['3'],
    }
    return phase_lists.get(workflow_mode, ['2', '2.5B', '3', '4', '5'])


def identify_missing_phases(
    tracker: AgentInvocationTracker,
    workflow_mode: str,
    task_type: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Identify which phases are missing from the invocation log.

    Args:
        tracker: Agent invocation tracker with recorded invocations
        workflow_mode: Workflow mode to determine expected phases
        task_type: Optional task_type string (propagated to
            ``get_expected_phase_list`` so declarative tasks in
            implement-only mode skip Phase 3 — TASK-ABSR-1357).

    Returns:
        List of dictionaries with 'phase' and 'description' for each missing phase

    Examples:
        >>> tracker = AgentInvocationTracker()
        >>> tracker.record_invocation('2', 'python-api-specialist', 'Planning')
        >>> tracker.mark_complete('2')
        >>> tracker.record_invocation('2.5B', 'architectural-reviewer', 'Review')
        >>> tracker.mark_complete('2.5B')
        >>> missing = identify_missing_phases(tracker, 'standard')
        >>> len(missing)
        3
        >>> missing[0]['phase']
        '3'
    """
    expected_phases = get_expected_phase_list(workflow_mode, task_type)
    completed_phases = [
        inv["phase"] for inv in tracker.invocations
        if inv["status"] == "completed"
    ]

    # Phase descriptions for error messages
    phase_descriptions = {
        '2': 'Planning',
        '2.5B': 'Architectural Review',
        '2.7': 'Complexity Evaluation',
        '3': 'Implementation',
        '4': 'Testing',
        '5': 'Code Review'
    }

    missing = []
    for phase in expected_phases:
        if phase not in completed_phases:
            missing.append({
                'phase': phase,
                'description': phase_descriptions.get(phase, 'Unknown')
            })

    return missing


def format_invocation_log(tracker: AgentInvocationTracker) -> str:
    """
    Format the invocation log for display in error messages.

    Args:
        tracker: Agent invocation tracker with recorded invocations

    Returns:
        Formatted string showing all invocations with status indicators

    Examples:
        >>> tracker = AgentInvocationTracker()
        >>> tracker.record_invocation('2', 'python-api-specialist', 'Planning')
        >>> tracker.mark_complete('2', duration_seconds=45)
        >>> log = format_invocation_log(tracker)
        >>> '✅ Phase 2' in log
        True
    """
    if not tracker.invocations:
        return "  (No invocations recorded)"

    lines = []
    for inv in tracker.invocations:
        status_icon = _get_status_icon(inv["status"])
        phase_label = f"Phase {inv['phase']}"
        if inv.get("phase_description"):
            phase_label += f" ({inv['phase_description']})"

        agent_info = _format_agent_info(inv)
        lines.append(f"{status_icon} {phase_label}: {agent_info}")

    return "\n".join(lines)


def _get_status_icon(status: str) -> str:
    """Get emoji icon for invocation status."""
    icons = {
        "completed": "✅",
        "in_progress": "⏳",
        "pending": "⏸️",
        "skipped": "❌"
    }
    return icons.get(status, "❓")


def _format_agent_info(inv: Dict[str, Any]) -> str:
    """Format agent information for display."""
    agent = inv["agent"]
    status = inv["status"]

    if status == "completed":
        duration = inv.get("duration", "?")
        return f"{agent} (completed in {duration}s)"
    elif status == "in_progress":
        return f"{agent} (IN PROGRESS)"
    elif status == "skipped":
        reason = inv.get("skip_reason", "Not invoked")
        return f"SKIPPED ({reason})"
    elif status == "pending":
        return "Pending"
    else:
        return agent


def validate_agent_invocations(
    tracker: AgentInvocationTracker,
    workflow_mode: str,
    task_type: Optional[str] = None,
) -> bool:
    """
    Validate that all required agents were invoked before generating final report.

    This is the main validation function that should be called before generating
    the completion report in task-work. It ensures that all expected phases have
    completed agent invocations.

    Args:
        tracker: Agent invocation tracker with recorded invocations
        workflow_mode: 'standard' | 'micro' | 'design-only' | 'implement-only'
        task_type: Optional task_type string (propagated to
            ``get_expected_phases`` / ``identify_missing_phases``).
            Declarative tasks in implement-only mode expect 2 phases
            (Testing, Code Review) instead of 3 (TASK-ABSR-1357).

    Raises:
        ValidationError: If invocations don't match expected phases with detailed
                        error message showing which phases were skipped

    Returns:
        bool: True if validation passes

    Examples:
        >>> tracker = AgentInvocationTracker()
        >>> # Record all required phases
        >>> for phase in ['2', '2.5B', '3', '4', '5']:
        ...     tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
        ...     tracker.mark_complete(phase, duration_seconds=30)
        >>> validate_agent_invocations(tracker, 'standard')
        True

        >>> tracker2 = AgentInvocationTracker()
        >>> # Missing phases
        >>> tracker2.record_invocation('2', 'agent', 'Planning')
        >>> tracker2.mark_complete('2')
        >>> validate_agent_invocations(tracker2, 'standard')  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        ValidationError: ❌ PROTOCOL VIOLATION...
    """
    expected = get_expected_phases(workflow_mode, task_type)
    actual = len([inv for inv in tracker.invocations if inv["status"] == "completed"])

    if actual < expected:
        missing_phases = identify_missing_phases(tracker, workflow_mode, task_type)
        invocation_log = format_invocation_log(tracker)

        # Build detailed error message
        error_lines = [
            "═" * 55,
            "❌ PROTOCOL VIOLATION: Agent invocation incomplete",
            "═" * 55,
            "",
            f"Expected: {expected} agent invocations",
            f"Actual: {actual} completed invocations",
            "",
            "Missing phases:"
        ]

        for missing in missing_phases:
            error_lines.append(f"  - Phase {missing['phase']} ({missing['description']})")

        error_lines.extend([
            "",
            "Cannot generate completion report until all agents are invoked.",
            "Review the AGENT INVOCATIONS LOG above to see which phases were skipped.",
            "",
            "AGENT INVOCATIONS LOG:",
            invocation_log,
            "",
            "TASK WILL BE MOVED TO BLOCKED STATE",
            "Reason: Protocol violation - required agents not invoked",
            "═" * 55
        ])

        raise ValidationError("\n".join(error_lines))

    return True


def validate_with_friendly_output(
    tracker: AgentInvocationTracker,
    workflow_mode: str
) -> tuple[bool, str]:
    """
    Validate agent invocations and return user-friendly output.

    This is a wrapper around validate_agent_invocations that catches the
    ValidationError and returns it as a string for easier display.

    Args:
        tracker: Agent invocation tracker with recorded invocations
        workflow_mode: Workflow mode identifier

    Returns:
        Tuple of (success: bool, message: str)
        - If success=True, message is a success confirmation
        - If success=False, message is the detailed error

    Examples:
        >>> tracker = AgentInvocationTracker()
        >>> for phase in ['2', '2.5B', '3', '4', '5']:
        ...     tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
        ...     tracker.mark_complete(phase, duration_seconds=30)
        >>> success, msg = validate_with_friendly_output(tracker, 'standard')
        >>> success
        True
        >>> 'Validation Passed' in msg
        True
    """
    try:
        validate_agent_invocations(tracker, workflow_mode)
        return True, "✅ Validation Passed: All required agents invoked\n"
    except ValidationError as e:
        return False, str(e)
