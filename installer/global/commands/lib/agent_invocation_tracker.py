"""
Agent Invocation Tracker for task-work execution visibility.

This module provides tracking for agent invocations during task-work execution,
recording which agents are invoked, their completion status, timing information,
and source paths for debugging and validation.

Task Reference: TASK-ENF2
Epic: agent-invocation-enforcement
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class AgentInvocationTracker:
    """
    Tracks agent invocations during task-work execution.

    Maintains a running log of which agents have been invoked,
    their completion status, source paths, and timing information.
    """

    def __init__(self):
        """Initialize the tracker with an empty invocation list."""
        self.invocations: List[Dict[str, Any]] = []

    def record_invocation(
        self,
        phase: str,
        agent_name: str,
        phase_description: str = "",
        agent_source: str = "unknown"
    ):
        """
        Record a new agent invocation.

        Args:
            phase: Phase identifier (e.g., "2", "2.5B", "3", "4", "5")
            agent_name: Name of the agent being invoked
            phase_description: Human-readable phase description
            agent_source: Source of agent (local/user/global/template)
        """
        # Remove pending placeholder if it exists for this phase
        self.invocations = [
            inv for inv in self.invocations
            if not (inv["phase"] == phase and inv["status"] == "pending")
        ]

        # Add the actual invocation
        self.invocations.append({
            "phase": phase,
            "agent": agent_name,
            "phase_description": phase_description,
            "agent_source": agent_source,
            "timestamp": datetime.now(),
            "status": "in_progress"
        })
        self.display_log()

    def mark_complete(
        self,
        phase: str,
        duration_seconds: Optional[int] = None,
        files_modified: Optional[List[str]] = None
    ):
        """
        Mark a phase as completed.

        Args:
            phase: Phase identifier to mark as complete
            duration_seconds: Time taken for agent execution
            files_modified: List of files modified by agent
        """
        for inv in self.invocations:
            if inv["phase"] == phase and inv["status"] == "in_progress":
                inv["status"] = "completed"
                inv["completed_at"] = datetime.now()
                if duration_seconds is not None:
                    inv["duration"] = duration_seconds
                if files_modified:
                    inv["files_modified"] = files_modified
                break
        self.display_log()

    def mark_skipped(self, phase: str, reason: str = "Not invoked"):
        """
        Mark a phase as skipped (for validation errors).

        Args:
            phase: Phase identifier to mark as skipped
            reason: Reason the phase was skipped
        """
        # Remove pending placeholder if it exists for this phase
        self.invocations = [
            inv for inv in self.invocations
            if not (inv["phase"] == phase and inv["status"] == "pending")
        ]

        # Check if this phase was recorded as in_progress
        phase_recorded = any(
            inv["phase"] == phase and inv["status"] in ["in_progress", "skipped"]
            for inv in self.invocations
        )

        if not phase_recorded:
            self.invocations.append({
                "phase": phase,
                "agent": "SKIPPED",
                "phase_description": "",
                "agent_source": "unknown",
                "timestamp": datetime.now(),
                "status": "skipped",
                "skip_reason": reason
            })
            self.display_log()

    def display_log(self):
        """
        Display the current invocation log with visual formatting.
        """
        print("\n" + "=" * 55)
        print("AGENT INVOCATIONS LOG")
        print("=" * 55)

        if not self.invocations:
            print("No agents invoked yet")
        else:
            for inv in self.invocations:
                status_icon = self._get_status_icon(inv["status"])
                phase_label = self._get_phase_label(
                    inv["phase"],
                    inv.get("phase_description", "")
                )
                agent_info = self._get_agent_info(inv)

                print(f"{status_icon} {phase_label}: {agent_info}")

        print("=" * 55 + "\n")

    def get_completed_count(self) -> int:
        """Return count of completed agent invocations."""
        return len([inv for inv in self.invocations if inv["status"] == "completed"])

    def get_invocations_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all invocations with specified status.

        Args:
            status: Status to filter by (completed, in_progress, pending, skipped)

        Returns:
            List of invocation dictionaries matching the status
        """
        return [inv for inv in self.invocations if inv["status"] == status]

    def add_pending_phase(
        self,
        phase: str,
        phase_description: str,
        agent_placeholder: str = "TBD"
    ):
        """
        Add a pending phase placeholder for visual clarity.

        Args:
            phase: Phase identifier
            phase_description: Human-readable phase description
            agent_placeholder: Placeholder agent name (default: "TBD")
        """
        # Only add if phase doesn't already exist
        phase_exists = any(inv["phase"] == phase for inv in self.invocations)
        if not phase_exists:
            self.invocations.append({
                "phase": phase,
                "agent": agent_placeholder,
                "phase_description": phase_description,
                "agent_source": "unknown",
                "status": "pending"
            })

    def _get_status_icon(self, status: str) -> str:
        """Get emoji icon for invocation status."""
        icons = {
            "completed": "✅",
            "in_progress": "⏳",
            "pending": "⏸️",
            "skipped": "❌"
        }
        return icons.get(status, "❓")

    def _get_phase_label(self, phase: str, description: str) -> str:
        """Format phase label with number and description."""
        if description:
            return f"Phase {phase} ({description})"
        return f"Phase {phase}"

    def _get_agent_info(self, inv: Dict[str, Any]) -> str:
        """Format agent information for display."""
        agent = inv["agent"]
        status = inv["status"]
        source = inv.get("agent_source", "unknown")

        # Format source indicator
        source_icon = self._get_source_icon(source)

        if status == "completed":
            duration = inv.get("duration", "?")
            return f"{agent} {source_icon} (source: {source}, completed in {duration}s)"
        elif status == "in_progress":
            return f"{agent} {source_icon} (source: {source}, IN PROGRESS)"
        elif status == "skipped":
            reason = inv.get("skip_reason", "Not invoked")
            return f"SKIPPED ({reason})"
        elif status == "pending":
            return "Pending"
        else:
            return f"{agent} {source_icon} (source: {source})"

    def _get_source_icon(self, source: str) -> str:
        """
        Get emoji icon for agent source.

        Args:
            source: Source string (local/user/global/template/template:name)

        Returns:
            Emoji icon for the source
        """
        # Handle template:name format
        if source.startswith("template:"):
            return "📦"

        # Map source to icon
        source_icons = {
            "local": "📁",
            "user": "👤",
            "global": "🌐",
            "template": "📦",
            "unknown": "❓"
        }
        return source_icons.get(source, "❓")


def add_pending_phases(tracker: AgentInvocationTracker, workflow_mode: str = "standard"):
    """
    Add pending phase placeholders to tracker for visual clarity.

    Args:
        tracker: Agent invocation tracker instance
        workflow_mode: Workflow mode to determine which phases to add
    """
    # Define all phases for standard workflow
    all_phases = [
        ("2", "Planning", "TBD"),
        ("2.5B", "Arch Review", "architectural-reviewer"),
        ("3", "Implementation", "TBD"),
        ("4", "Testing", "TBD"),
        ("5", "Review", "code-reviewer")
    ]

    # For micro workflow, only add relevant phases
    if workflow_mode == "micro":
        all_phases = [
            ("3", "Implementation", "TBD"),
            ("4", "Testing", "TBD"),
            ("5", "Review", "code-reviewer")
        ]

    # Add pending phases that haven't been invoked yet
    for phase, desc, agent in all_phases:
        tracker.add_pending_phase(phase, desc, agent)
