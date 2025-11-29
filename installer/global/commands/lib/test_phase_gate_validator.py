"""
Unit tests for PhaseGateValidator.

Tests phase gate validation checkpoints that ensure agents
are properly invoked before allowing phase progression.

Task Reference: TASK-ENF4
Epic: agent-invocation-enforcement
"""

import unittest
from datetime import datetime
from agent_invocation_tracker import AgentInvocationTracker
from phase_gate_validator import PhaseGateValidator, ValidationError


class TestPhaseGateValidator(unittest.TestCase):
    """Test suite for PhaseGateValidator class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.tracker = AgentInvocationTracker()
        self.validator = PhaseGateValidator(self.tracker)

    def test_validation_passes_when_agent_invoked(self):
        """Test that validation passes when phase agent is invoked and completed."""
        # Record and complete an invocation for Phase 3
        self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
        self.tracker.mark_complete("3", duration_seconds=120)

        # Validation should pass
        result = self.validator.validate_phase_completion("3", "Implementation")
        self.assertTrue(result)

    def test_validation_fails_when_agent_not_invoked(self):
        """Test that validation fails when phase agent is not invoked."""
        # No invocations recorded for Phase 3

        # Validation should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            self.validator.validate_phase_completion("3", "Implementation")

        # Error message should mention phase gate violation
        error_msg = str(context.exception)
        self.assertIn("PHASE GATE VIOLATION", error_msg)
        self.assertIn("Phase 3", error_msg)
        self.assertIn("agent not invoked", error_msg)

    def test_validation_fails_when_agent_only_in_progress(self):
        """Test that validation fails when agent is in_progress but not completed."""
        # Record invocation but don't mark as complete
        self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")

        # Validation should fail (requires completed status)
        with self.assertRaises(ValidationError):
            self.validator.validate_phase_completion("3", "Implementation")

    def test_validation_fails_when_agent_skipped(self):
        """Test that validation fails when phase is marked as skipped."""
        # Mark phase as skipped
        self.tracker.mark_skipped("3", "Compilation failed")

        # Validation should fail
        with self.assertRaises(ValidationError):
            self.validator.validate_phase_completion("3", "Implementation")

    def test_multiple_phases_can_be_validated(self):
        """Test that multiple phases can be validated independently."""
        # Record and complete Phase 2
        self.tracker.record_invocation("2", "task-manager", "Planning", "global")
        self.tracker.mark_complete("2", duration_seconds=45)

        # Record and complete Phase 3
        self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
        self.tracker.mark_complete("3", duration_seconds=120)

        # Both validations should pass
        self.assertTrue(self.validator.validate_phase_completion("2", "Planning"))
        self.assertTrue(self.validator.validate_phase_completion("3", "Implementation"))

    def test_validation_error_shows_expected_agent(self):
        """Test that validation error shows correct expected agent for each phase."""
        test_cases = [
            ("2", "Planning", "{planning_agent}"),
            ("2.5B", "Architectural Review", "architectural-reviewer"),
            ("3", "Implementation", "{implementation_agent}"),
            ("4", "Testing", "{testing_agent}"),
            ("5", "Code Review", "code-reviewer")
        ]

        for phase, phase_name, expected_agent in test_cases:
            # No invocations for this phase
            with self.assertRaises(ValidationError) as context:
                self.validator.validate_phase_completion(phase, phase_name)

            error_msg = str(context.exception)
            self.assertIn(f"Phase {phase}", error_msg)
            self.assertIn(expected_agent, error_msg)

    def test_validation_error_shows_invocation_format(self):
        """Test that validation error includes proper invocation format guidance."""
        with self.assertRaises(ValidationError) as context:
            self.validator.validate_phase_completion("3", "Implementation")

        error_msg = str(context.exception)
        # Should show how to invoke the agent
        self.assertIn("subagent_type:", error_msg)
        self.assertIn("description:", error_msg)
        self.assertIn("prompt:", error_msg)

    def test_validation_error_mentions_blocked_state(self):
        """Test that validation error mentions task will be moved to BLOCKED."""
        with self.assertRaises(ValidationError) as context:
            self.validator.validate_phase_completion("3", "Implementation")

        error_msg = str(context.exception)
        self.assertIn("TASK MOVED TO BLOCKED STATE", error_msg)
        self.assertIn("Phase gate violation", error_msg)

    def test_get_expected_agent_returns_correct_agents(self):
        """Test that _get_expected_agent returns correct agent names."""
        expected_agents = {
            "2": "{planning_agent}",
            "2.5B": "architectural-reviewer",
            "3": "{implementation_agent}",
            "4": "{testing_agent}",
            "5": "code-reviewer"
        }

        for phase, expected_agent in expected_agents.items():
            actual_agent = self.validator._get_expected_agent(phase)
            self.assertEqual(actual_agent, expected_agent)

    def test_get_expected_agent_returns_placeholder_for_unknown_phase(self):
        """Test that _get_expected_agent returns placeholder for unknown phases."""
        unknown_phases = ["1", "6", "99", "invalid"]

        for phase in unknown_phases:
            actual_agent = self.validator._get_expected_agent(phase)
            self.assertEqual(actual_agent, "{agent}")

    def test_get_phase_description_returns_correct_descriptions(self):
        """Test that _get_phase_description returns correct descriptions."""
        expected_descriptions = {
            "2": "Plan implementation for TASK-XXX",
            "2.5B": "Review architecture for TASK-XXX",
            "3": "Implement TASK-XXX",
            "4": "Generate and execute tests for TASK-XXX",
            "5": "Review TASK-XXX implementation"
        }

        for phase, expected_desc in expected_descriptions.items():
            actual_desc = self.validator._get_phase_description(phase)
            self.assertEqual(actual_desc, expected_desc)

    def test_get_phase_description_returns_generic_for_unknown_phase(self):
        """Test that _get_phase_description returns generic description for unknown phases."""
        unknown_phases = ["1", "6", "99"]

        for phase in unknown_phases:
            actual_desc = self.validator._get_phase_description(phase)
            self.assertEqual(actual_desc, "Execute phase")

    def test_validation_success_prints_confirmation(self):
        """Test that successful validation prints confirmation message."""
        import io
        import sys

        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            # Record and complete invocation
            self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
            self.tracker.mark_complete("3", duration_seconds=120)

            # Validate (should print success message)
            self.validator.validate_phase_completion("3", "Implementation")

            # Check output contains confirmation
            output = captured_output.getvalue()
            self.assertIn("✅", output)
            self.assertIn("Phase 3 Gate", output)
            self.assertIn("Agent invocation confirmed", output)

        finally:
            # Restore stdout
            sys.stdout = sys.__stdout__

    def test_validation_with_multiple_invocations_same_phase(self):
        """Test validation when phase has multiple invocations (e.g., retry scenarios)."""
        # First invocation (failed)
        self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
        self.tracker.mark_skipped("3", "First attempt failed")

        # Second invocation (succeeded)
        self.tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
        self.tracker.mark_complete("3", duration_seconds=150)

        # Validation should pass (at least one completed invocation exists)
        result = self.validator.validate_phase_completion("3", "Implementation")
        self.assertTrue(result)

    def test_architectural_review_phase_special_case(self):
        """Test validation for architectural review phase (Phase 2.5B)."""
        # Record and complete architectural review
        self.tracker.record_invocation("2.5B", "architectural-reviewer", "Arch Review", "global")
        self.tracker.mark_complete("2.5B", duration_seconds=30)

        # Validation should pass
        result = self.validator.validate_phase_completion("2.5B", "Architectural Review")
        self.assertTrue(result)

    def test_validation_error_format_is_readable(self):
        """Test that validation error is well-formatted and readable."""
        with self.assertRaises(ValidationError) as context:
            self.validator.validate_phase_completion("3", "Implementation")

        error_msg = str(context.exception)

        # Should have visual separators
        self.assertIn("═", error_msg)

        # Should have clear sections
        self.assertIn("Expected:", error_msg)
        self.assertIn("Actual:", error_msg)

        # Should have actionable guidance
        self.assertIn("Please invoke the agent using:", error_msg)

    def test_integration_with_tracker_workflow(self):
        """Test validator integrates correctly with full tracker workflow."""
        # Simulate full workflow
        phases = [
            ("2", "task-manager", "Planning", "global"),
            ("2.5B", "architectural-reviewer", "Arch Review", "global"),
            ("3", "python-api-specialist", "Implementation", "local"),
            ("4", "test-orchestrator", "Testing", "global"),
            ("5", "code-reviewer", "Review", "global")
        ]

        # Execute workflow
        for phase, agent, desc, source in phases:
            self.tracker.record_invocation(phase, agent, desc, source)
            self.tracker.mark_complete(phase, duration_seconds=60)

            # Validate each phase
            result = self.validator.validate_phase_completion(phase, desc)
            self.assertTrue(result)

        # All phases should be completed
        self.assertEqual(self.tracker.get_completed_count(), 5)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
