"""
State-aware design change handlers.

Provides different handling policies based on task state:
- BACKLOG: Silent cache refresh
- IN_PROGRESS: Pause and notify user
- IN_REVIEW: Flag in review notes
- COMPLETED: Require new task
"""

from typing import Dict, Any


def handle_design_change(task_state: str, change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle design change based on task state.

    Args:
        task_state: Current task state (BACKLOG, IN_PROGRESS, IN_REVIEW, COMPLETED)
        change_info: Change detection results with 'changed', 'old_hash', 'new_hash'

    Returns:
        Dict with:
            - action: str (action to take)
            - notify_user: bool
            - message: str (optional)
            - options: list (optional, for IN_PROGRESS)
            - notify_reviewer: bool (optional, for IN_REVIEW)
            - review_note: str (optional, for IN_REVIEW)
    """
    if not change_info.get("changed"):
        return {
            "action": "no_action",
            "notify_user": False,
        }

    # State-specific handlers
    if task_state == "BACKLOG":
        return _handle_backlog_state(change_info)
    elif task_state == "IN_PROGRESS":
        return _handle_in_progress_state(change_info)
    elif task_state == "IN_REVIEW":
        return _handle_in_review_state(change_info)
    elif task_state == "COMPLETED":
        return _handle_completed_state(change_info)
    else:
        # Unknown state, default to pause and notify
        return _handle_in_progress_state(change_info)


def _handle_backlog_state(change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle design change for BACKLOG state.

    Policy: Silent cache refresh, no user notification needed.

    Args:
        change_info: Change detection results

    Returns:
        Action dict with silent_refresh action
    """
    return {
        "action": "silent_refresh",
        "notify_user": False,
        "message": "Design updated in BACKLOG. Cache refreshed silently.",
    }


def _handle_in_progress_state(change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle design change for IN_PROGRESS state.

    Policy: Pause after current cycle, notify user with continue/restart options.

    Args:
        change_info: Change detection results

    Returns:
        Action dict with pause_and_notify action
    """
    old_hash = change_info.get("old_hash", "unknown")
    new_hash = change_info.get("new_hash", "unknown")

    return {
        "action": "pause_and_notify",
        "notify_user": True,
        "message": (
            f"Design has changed since extraction.\n"
            f"Old hash: {old_hash}\n"
            f"New hash: {new_hash}\n"
            f"Please choose how to proceed."
        ),
        "options": ["continue", "restart"],
    }


def _handle_in_review_state(change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle design change for IN_REVIEW state.

    Policy: Flag design change in review notes for reviewer decision.

    Args:
        change_info: Change detection results

    Returns:
        Action dict with flag_in_review action
    """
    old_hash = change_info.get("old_hash", "unknown")
    new_hash = change_info.get("new_hash", "unknown")

    review_note = (
        f"DESIGN UPDATED: Design changed since implementation.\n"
        f"- Implementation based on: {old_hash}\n"
        f"- Current design version: {new_hash}\n"
        f"Reviewer should verify implementation against current design."
    )

    return {
        "action": "flag_in_review",
        "notify_reviewer": True,
        "review_note": review_note,
        "message": "Design updated since implementation. Review notes updated.",
    }


def _handle_completed_state(change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle design change for COMPLETED state.

    Policy: No automatic re-processing. Require new task for design updates.

    Args:
        change_info: Change detection results

    Returns:
        Action dict with require_new_task action
    """
    return {
        "action": "require_new_task",
        "notify_user": True,
        "message": (
            "Design has changed after task completion. "
            "No automatic re-processing. "
            "Create a new task to implement design updates."
        ),
    }
