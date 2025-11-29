"""
Phase Gate Validator for task-work execution.

This module provides validation checkpoints after each phase to ensure
that agents were properly invoked via the Task tool before allowing
progression to the next phase.

Task Reference: TASK-ENF4
Epic: agent-invocation-enforcement
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_invocation_tracker import AgentInvocationTracker


class ValidationError(Exception):
    """Raised when phase gate validation fails."""
    pass


class PhaseGateValidator:
    """
    Validates that agents were properly invoked after each phase.

    Prevents progression to next phase if current phase's agent
    was not invoked via Task tool.
    """

    def __init__(self, tracker: "AgentInvocationTracker"):
        """
        Initialize the validator with an invocation tracker.

        Args:
            tracker: AgentInvocationTracker instance to check invocations
        """
        self.tracker = tracker

    def validate_phase_completion(self, phase: str, phase_name: str) -> bool:
        """
        Validate that the current phase's agent was actually invoked.

        This runs AFTER each phase to ensure Task tool was used.

        Args:
            phase: Phase identifier (e.g., "3", "4", "5")
            phase_name: Human-readable phase name (e.g., "Implementation")

        Raises:
            ValidationError: If phase agent was not invoked

        Returns:
            bool: True if validation passes
        """
        # Check if phase was completed in tracker
        phase_invocations = [
            inv for inv in self.tracker.invocations
            if inv["phase"] == phase and inv["status"] == "completed"
        ]

        if len(phase_invocations) == 0:
            raise ValidationError(
                self._format_violation_error(phase, phase_name)
            )

        # Validation passed
        print(f"✅ Phase {phase} Gate: Agent invocation confirmed\n")
        return True

    def _format_violation_error(self, phase: str, phase_name: str) -> str:
        """
        Format detailed error message for phase gate violation.

        Args:
            phase: Phase identifier
            phase_name: Human-readable phase name

        Returns:
            Formatted error message
        """
        expected_agent = self._get_expected_agent(phase)

        return f"""
═══════════════════════════════════════════════════════
❌ PHASE GATE VIOLATION: Phase {phase} agent not invoked
═══════════════════════════════════════════════════════

The protocol requires using the Task tool to invoke a specialized agent.
Phase {phase} ({phase_name}) appears to have been completed without agent invocation.

Expected: INVOKE Task tool with subagent_type='{expected_agent}'
Actual: No Task tool invocation detected

Cannot proceed to next phase until Phase {phase} agent is invoked.

Please invoke the agent using:
  subagent_type: "{expected_agent}"
  description: "{self._get_phase_description(phase)}"
  prompt: "..."

TASK MOVED TO BLOCKED STATE
Reason: Phase gate violation - Phase {phase} agent not invoked
═══════════════════════════════════════════════════════
"""

    def _get_expected_agent(self, phase: str) -> str:
        """
        Get the expected agent name for a given phase.

        Args:
            phase: Phase identifier

        Returns:
            Expected agent name (placeholder if unknown)
        """
        phase_agents = {
            "2": "{planning_agent}",
            "2.5B": "architectural-reviewer",
            "3": "{implementation_agent}",
            "4": "{testing_agent}",
            "5": "code-reviewer"
        }
        return phase_agents.get(phase, "{agent}")

    def _get_phase_description(self, phase: str) -> str:
        """
        Get human-readable description for a given phase.

        Args:
            phase: Phase identifier

        Returns:
            Phase description
        """
        descriptions = {
            "2": "Plan implementation for TASK-XXX",
            "2.5B": "Review architecture for TASK-XXX",
            "3": "Implement TASK-XXX",
            "4": "Generate and execute tests for TASK-XXX",
            "5": "Review TASK-XXX implementation"
        }
        return descriptions.get(phase, "Execute phase")
