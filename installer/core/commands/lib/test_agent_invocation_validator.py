"""
Unit tests for agent invocation validator.

Tests validation logic that prevents false reporting by ensuring all
required agents were actually invoked before generating completion reports.

Task Reference: TASK-ENF1
Epic: agent-invocation-enforcement
"""

import pytest
from agent_invocation_tracker import AgentInvocationTracker
from agent_invocation_validator import (
    get_expected_phases,
    get_expected_phase_list,
    identify_missing_phases,
    validate_agent_invocations,
    validate_with_friendly_output,
    ValidationError
)


class TestGetExpectedPhases:
    """Test phase count expectations for different workflow modes."""

    def test_standard_workflow_expects_5_phases(self):
        """Standard workflow should expect 5 agent invocations."""
        assert get_expected_phases('standard') == 5

    def test_micro_workflow_expects_3_phases(self):
        """Micro workflow should expect 3 agent invocations."""
        assert get_expected_phases('micro') == 3

    def test_design_only_workflow_expects_3_phases(self):
        """Design-only workflow should expect 3 agent invocations."""
        assert get_expected_phases('design-only') == 3

    def test_implement_only_workflow_expects_3_phases(self):
        """Implement-only workflow should expect 3 agent invocations."""
        assert get_expected_phases('implement-only') == 3

    def test_unknown_workflow_defaults_to_5_phases(self):
        """Unknown workflow mode should default to 5 phases (standard)."""
        assert get_expected_phases('unknown') == 5
        assert get_expected_phases('invalid') == 5


class TestGetExpectedPhaseList:
    """Test phase identifier lists for different workflow modes."""

    def test_standard_workflow_phase_list(self):
        """Standard workflow should have all 5 phases."""
        phases = get_expected_phase_list('standard')
        assert phases == ['2', '2.5B', '3', '4', '5']

    def test_micro_workflow_phase_list(self):
        """Micro workflow should skip planning and arch review."""
        phases = get_expected_phase_list('micro')
        assert phases == ['3', '4', '5']
        assert '2' not in phases
        assert '2.5B' not in phases

    def test_design_only_workflow_phase_list(self):
        """Design-only workflow should only have planning phases."""
        phases = get_expected_phase_list('design-only')
        assert phases == ['2', '2.5B', '2.7']
        assert '3' not in phases
        assert '4' not in phases
        assert '5' not in phases

    def test_implement_only_workflow_phase_list(self):
        """Implement-only workflow should skip planning phases."""
        phases = get_expected_phase_list('implement-only')
        assert phases == ['3', '4', '5']
        assert '2' not in phases
        assert '2.5B' not in phases


class TestIdentifyMissingPhases:
    """Test identification of missing phases in invocation log."""

    def test_no_missing_phases_when_all_completed(self):
        """Should return empty list when all phases completed."""
        tracker = AgentInvocationTracker()

        # Complete all standard workflow phases
        for phase in ['2', '2.5B', '3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        missing = identify_missing_phases(tracker, 'standard')
        assert missing == []

    def test_identifies_single_missing_phase(self):
        """Should identify when one phase is missing."""
        tracker = AgentInvocationTracker()

        # Complete phases except Phase 3
        for phase in ['2', '2.5B', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        missing = identify_missing_phases(tracker, 'standard')
        assert len(missing) == 1
        assert missing[0]['phase'] == '3'
        assert missing[0]['description'] == 'Implementation'

    def test_identifies_multiple_missing_phases(self):
        """Should identify multiple missing phases."""
        tracker = AgentInvocationTracker()

        # Only complete Phase 2 and 5
        for phase in ['2', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        missing = identify_missing_phases(tracker, 'standard')
        assert len(missing) == 3
        missing_phase_ids = [m['phase'] for m in missing]
        assert '2.5B' in missing_phase_ids
        assert '3' in missing_phase_ids
        assert '4' in missing_phase_ids

    def test_missing_phases_have_descriptions(self):
        """Missing phases should include human-readable descriptions."""
        tracker = AgentInvocationTracker()

        # Complete only Phase 2
        tracker.record_invocation('2', 'agent', 'Planning')
        tracker.mark_complete('2')

        missing = identify_missing_phases(tracker, 'standard')
        for phase in missing:
            assert 'phase' in phase
            assert 'description' in phase
            assert phase['description'] != 'Unknown'


class TestValidateAgentInvocations:
    """Test validation logic for agent invocations."""

    def test_validation_passes_with_all_phases_completed(self):
        """Should pass validation when all required phases completed."""
        tracker = AgentInvocationTracker()

        # Complete all standard workflow phases
        for phase in ['2', '2.5B', '3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        # Should not raise exception
        result = validate_agent_invocations(tracker, 'standard')
        assert result is True

    def test_validation_fails_with_missing_phases(self):
        """Should raise ValidationError when phases are missing."""
        tracker = AgentInvocationTracker()

        # Only complete 2 phases (need 5 for standard)
        for phase in ['2', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'PROTOCOL VIOLATION' in error_message
        assert 'Expected: 5' in error_message
        assert 'Actual: 2' in error_message

    def test_validation_error_lists_missing_phases(self):
        """Validation error should list specific missing phases."""
        tracker = AgentInvocationTracker()

        # Complete only Phase 2
        tracker.record_invocation('2', 'agent', 'Planning')
        tracker.mark_complete('2')

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'Phase 2.5B' in error_message
        assert 'Phase 3' in error_message
        assert 'Phase 4' in error_message
        assert 'Phase 5' in error_message

    def test_validation_error_includes_invocation_log(self):
        """Validation error should include formatted invocation log."""
        tracker = AgentInvocationTracker()

        # Complete Phase 2 and 5
        tracker.record_invocation('2', 'python-api-specialist', 'Planning')
        tracker.mark_complete('2', duration_seconds=45)
        tracker.record_invocation('5', 'code-reviewer', 'Review')
        tracker.mark_complete('5', duration_seconds=20)

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'AGENT INVOCATIONS LOG' in error_message
        assert 'python-api-specialist' in error_message
        assert 'code-reviewer' in error_message

    def test_validation_respects_workflow_mode(self):
        """Validation should use correct phase count for workflow mode."""
        tracker = AgentInvocationTracker()

        # Complete 3 phases (enough for micro, not for standard)
        for phase in ['3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        # Should pass for micro workflow
        result = validate_agent_invocations(tracker, 'micro')
        assert result is True

        # Should fail for standard workflow
        with pytest.raises(ValidationError):
            validate_agent_invocations(tracker, 'standard')

    def test_validation_ignores_in_progress_invocations(self):
        """Validation should only count completed invocations."""
        tracker = AgentInvocationTracker()

        # Record 5 invocations but only complete 3
        for phase in ['2', '2.5B', '3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')

        # Only mark 3 as complete
        for phase in ['2', '3', '5']:
            tracker.mark_complete(phase, duration_seconds=30)

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'Actual: 3 completed invocations' in error_message

    def test_validation_ignores_skipped_invocations(self):
        """Validation should not count skipped phases as completed."""
        tracker = AgentInvocationTracker()

        # Complete 4 phases
        for phase in ['2', '2.5B', '3', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        # Mark Phase 4 as skipped
        tracker.mark_skipped('4', reason='Test skipped')

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'Actual: 4 completed invocations' in error_message
        assert 'Phase 4' in error_message


class TestValidateWithFriendlyOutput:
    """Test user-friendly validation wrapper."""

    def test_success_returns_true_and_success_message(self):
        """Should return True with success message when validation passes."""
        tracker = AgentInvocationTracker()

        # Complete all micro workflow phases
        for phase in ['3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        success, message = validate_with_friendly_output(tracker, 'micro')
        assert success is True
        assert '✅ Validation Passed' in message
        assert 'All required agents invoked' in message

    def test_failure_returns_false_and_error_message(self):
        """Should return False with error message when validation fails."""
        tracker = AgentInvocationTracker()

        # Complete only 1 phase (need 3 for micro)
        tracker.record_invocation('3', 'agent', 'Implementation')
        tracker.mark_complete('3')

        success, message = validate_with_friendly_output(tracker, 'micro')
        assert success is False
        assert 'PROTOCOL VIOLATION' in message
        assert 'Expected: 3' in message
        assert 'Actual: 1' in message

    def test_error_message_contains_full_details(self):
        """Error message should contain all validation details."""
        tracker = AgentInvocationTracker()

        tracker.record_invocation('2', 'agent', 'Planning')
        tracker.mark_complete('2')

        success, message = validate_with_friendly_output(tracker, 'standard')
        assert success is False
        assert 'Missing phases:' in message
        assert 'AGENT INVOCATIONS LOG' in message
        assert 'BLOCKED STATE' in message


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_tracker_fails_validation(self):
        """Empty tracker should fail validation."""
        tracker = AgentInvocationTracker()

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        assert 'Expected: 5' in error_message
        assert 'Actual: 0' in error_message

    def test_validation_with_unknown_workflow_uses_standard(self):
        """Unknown workflow mode should default to standard (5 phases)."""
        tracker = AgentInvocationTracker()

        # Complete 3 phases
        for phase in ['3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        # Should fail because unknown defaults to standard (needs 5)
        with pytest.raises(ValidationError):
            validate_agent_invocations(tracker, 'unknown_mode')

    def test_extra_completed_phases_dont_cause_failure(self):
        """Having more completed phases than expected should not fail."""
        tracker = AgentInvocationTracker()

        # Complete 6 phases (more than standard's 5)
        for phase in ['2', '2.5A', '2.5B', '3', '4', '5']:
            tracker.record_invocation(phase, f'agent-{phase}', f'Phase {phase}')
            tracker.mark_complete(phase, duration_seconds=30)

        # Should pass (6 >= 5)
        result = validate_agent_invocations(tracker, 'standard')
        assert result is True

    def test_validation_error_message_formatting(self):
        """Validation error should be well-formatted with separators."""
        tracker = AgentInvocationTracker()

        tracker.record_invocation('2', 'agent', 'Planning')
        tracker.mark_complete('2')

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(tracker, 'standard')

        error_message = str(exc_info.value)
        # Check for separator lines
        assert '═' * 55 in error_message
        # Check for clear sections
        assert 'PROTOCOL VIOLATION' in error_message
        assert 'Missing phases:' in error_message
        assert 'AGENT INVOCATIONS LOG:' in error_message


class TestWorkflowModeScenarios:
    """Test real-world workflow scenarios."""

    def test_standard_workflow_complete_scenario(self):
        """Full standard workflow with all 5 phases."""
        tracker = AgentInvocationTracker()

        # Simulate full standard workflow
        phases = [
            ('2', 'python-api-specialist', 'Planning', 45),
            ('2.5B', 'architectural-reviewer', 'Arch Review', 30),
            ('3', 'python-api-specialist', 'Implementation', 120),
            ('4', 'test-orchestrator', 'Testing', 60),
            ('5', 'code-reviewer', 'Review', 20)
        ]

        for phase, agent, desc, duration in phases:
            tracker.record_invocation(phase, agent, desc)
            tracker.mark_complete(phase, duration_seconds=duration)

        # Should pass
        result = validate_agent_invocations(tracker, 'standard')
        assert result is True

    def test_micro_workflow_complete_scenario(self):
        """Full micro workflow with 3 phases (skips planning)."""
        tracker = AgentInvocationTracker()

        # Simulate micro workflow
        phases = [
            ('3', 'python-api-specialist', 'Implementation', 60),
            ('4', 'test-orchestrator', 'Testing', 30),
            ('5', 'code-reviewer', 'Quick Review', 15)
        ]

        for phase, agent, desc, duration in phases:
            tracker.record_invocation(phase, agent, desc)
            tracker.mark_complete(phase, duration_seconds=duration)

        # Should pass for micro
        result = validate_agent_invocations(tracker, 'micro')
        assert result is True

        # Should fail for standard (needs 5 phases)
        with pytest.raises(ValidationError):
            validate_agent_invocations(tracker, 'standard')

    def test_design_only_workflow_scenario(self):
        """Design-only workflow stops before implementation."""
        tracker = AgentInvocationTracker()

        # Simulate design-only workflow
        phases = [
            ('2', 'python-api-specialist', 'Planning', 45),
            ('2.5B', 'architectural-reviewer', 'Arch Review', 30),
            ('2.7', 'complexity-evaluator', 'Complexity', 15)
        ]

        for phase, agent, desc, duration in phases:
            tracker.record_invocation(phase, agent, desc)
            tracker.mark_complete(phase, duration_seconds=duration)

        # Should pass for design-only
        result = validate_agent_invocations(tracker, 'design-only')
        assert result is True

    def test_implement_only_workflow_scenario(self):
        """Implement-only workflow starts from implementation."""
        tracker = AgentInvocationTracker()

        # Simulate implement-only workflow (design already approved)
        phases = [
            ('3', 'python-api-specialist', 'Implementation', 90),
            ('4', 'test-orchestrator', 'Testing', 45),
            ('5', 'code-reviewer', 'Review', 25)
        ]

        for phase, agent, desc, duration in phases:
            tracker.record_invocation(phase, agent, desc)
            tracker.mark_complete(phase, duration_seconds=duration)

        # Should pass for implement-only
        result = validate_agent_invocations(tracker, 'implement-only')
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
