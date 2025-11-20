"""
Unit tests for resume routing logic in run() method.

Tests explicit phase handlers for checkpoint-resume pattern:
- Phase 5: _run_from_phase_5()
- Phase 7: _run_from_phase_7()
- Phase 7.5: _run_from_phase_7() (same as 7)

TASK-PHASE-7-5-FIX-FOUNDATION: Explicit phase routing improvement
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))


def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


orchestrator_module = import_module_from_path(
    "template_create_orchestrator",
    commands_lib_path / "template_create_orchestrator.py"
)

TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
OrchestrationConfig = orchestrator_module.OrchestrationConfig
WorkflowPhase = orchestrator_module.WorkflowPhase


# ========== Test Fixtures ==========

@pytest.fixture
def mock_config():
    """Mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.codebase_path = Path("/test/codebase")
    config.output_path = None
    config.output_location = "global"
    config.dry_run = False
    config.resume = True
    config.verbose = False
    return config


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_orchestrator_no_init(mock_config):
    """Create orchestrator with mocked __init__."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orchestrator = TemplateCreateOrchestrator(mock_config)
        orchestrator.config = mock_config
        orchestrator.errors = []
        orchestrator.warnings = []
        orchestrator.manifest = Mock(name="test-template")
        orchestrator.manifest.confidence_score = 85
        # TASK-PHASE-7-5-FIX-FOUNDATION: Initialize state_manager for resume tests
        orchestrator.state_manager = Mock()
        orchestrator.agent_invoker = Mock()
        return orchestrator


# ========== Helper Functions ==========

def setup_mock_state_manager(orchestrator, phase, checkpoint=None):
    """
    Configure state manager for resume routing tests.

    Args:
        orchestrator: Mock orchestrator instance
        phase: WorkflowPhase constant to resume from
        checkpoint: Optional checkpoint data

    Returns:
        Mock state object configured for testing
    """
    state = Mock()
    state.phase = phase
    if checkpoint:
        state.checkpoint = checkpoint

    orchestrator.state_manager.load_state.return_value = state
    return state


# ========== Unit Tests: Resume Routing ==========

class TestResumeRouting:
    """Test resume routing logic in run() method."""

    @pytest.mark.parametrize("phase,expected_handler", [
        (WorkflowPhase.PHASE_5, '_run_from_phase_5'),
        (WorkflowPhase.PHASE_7, '_run_from_phase_7'),
        # REMOVED: Phase 7.5 test (TASK-SIMP-9ABE)
    ])
    def test_phase_routing(self, mock_orchestrator_no_init, phase, expected_handler):
        """Test routing to correct handler based on phase."""
        mock_orchestrator_no_init.config.resume = True

        # Setup state using helper function
        setup_mock_state_manager(mock_orchestrator_no_init, phase)

        # Mock the phase handler
        with patch.object(mock_orchestrator_no_init, expected_handler) as mock_run:
            mock_run.return_value = Mock(success=True)

            result = mock_orchestrator_no_init.run()

            # Verify correct handler was called
            mock_run.assert_called_once()

    def test_defaults_to_phase_5_for_unknown_phase(self, mock_orchestrator_no_init):
        """Test unknown phase defaults to _run_from_phase_5."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, 2)  # Unknown phase

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_5') as mock_run:
            mock_run.return_value = Mock(success=True)

            result = mock_orchestrator_no_init.run()

            # Should fall back to _run_from_phase_5
            mock_run.assert_called_once()

    def test_skips_routing_when_not_resuming(self, mock_orchestrator_no_init):
        """Test routing is skipped when resume is False."""
        mock_orchestrator_no_init.config.resume = False

        with patch.object(mock_orchestrator_no_init, '_run_all_phases') as mock_run:
            mock_run.return_value = Mock(success=True)

            result = mock_orchestrator_no_init.run()

            # Should call _run_all_phases instead of phase-specific handlers
            mock_run.assert_called_once()


# ========== Unit Tests: Phase 5 Routing ==========

class TestPhase5Routing:
    """Test routing to Phase 5 handler."""

    def test_phase_5_handler_is_called(self, mock_orchestrator_no_init):
        """Test _run_from_phase_5 is called for Phase 5."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_5)

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_5') as mock_run:
            mock_run.return_value = Mock(success=True)
            result = mock_orchestrator_no_init.run()

            assert mock_run.called

    def test_phase_5_with_agent_invocation(self, mock_orchestrator_no_init):
        """Test Phase 5 continues after agent invocation."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_5)

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_5') as mock_run:
            mock_run.return_value = Mock(success=True, errors=[])
            result = mock_orchestrator_no_init.run()

            # Verify handler was invoked
            assert mock_run.called


# ========== Unit Tests: Phase 7 Routing ==========

class TestPhase7Routing:
    """Test routing to Phase 7 handler."""

    def test_phase_7_handler_is_called(self, mock_orchestrator_no_init):
        """Test _run_from_phase_7 is called for Phase 7."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_7)

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_7') as mock_run:
            mock_run.return_value = Mock(success=True)
            result = mock_orchestrator_no_init.run()

            assert mock_run.called

    # REMOVED: test_phase_7_5_routes_to_phase_7_handler (TASK-SIMP-9ABE)

    def test_phase_7_with_agent_enhancement(self, mock_orchestrator_no_init):
        """Test Phase 7 continues after agent enhancement."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_7)

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_7') as mock_run:
            mock_run.return_value = Mock(success=True, errors=[])
            result = mock_orchestrator_no_init.run()

            # Verify handler was invoked
            assert mock_run.called


# ========== Unit Tests: Explicit Phase Handlers ==========

class TestExplicitPhaseHandlers:
    """Test explicit phase handler methods exist and are distinct."""

    def test_run_from_phase_5_exists(self, mock_orchestrator_no_init):
        """Test _run_from_phase_5 method exists."""
        assert hasattr(mock_orchestrator_no_init, '_run_from_phase_5')
        assert callable(mock_orchestrator_no_init._run_from_phase_5)

    def test_run_from_phase_7_exists(self, mock_orchestrator_no_init):
        """Test _run_from_phase_7 method exists."""
        assert hasattr(mock_orchestrator_no_init, '_run_from_phase_7')
        assert callable(mock_orchestrator_no_init._run_from_phase_7)

    def test_run_all_phases_exists(self, mock_orchestrator_no_init):
        """Test _run_all_phases method exists."""
        assert hasattr(mock_orchestrator_no_init, '_run_all_phases')
        assert callable(mock_orchestrator_no_init._run_all_phases)

    def test_phase_handlers_are_distinct(self, mock_orchestrator_no_init):
        """Test phase handlers are distinct methods."""
        handler_5 = mock_orchestrator_no_init._run_from_phase_5
        handler_7 = mock_orchestrator_no_init._run_from_phase_7
        handler_all = mock_orchestrator_no_init._run_all_phases

        # All should be different methods
        assert handler_5 != handler_7
        assert handler_7 != handler_all
        assert handler_5 != handler_all


# ========== Integration Tests ==========

class TestResumeRoutingIntegration:
    """Integration tests for resume routing."""

    def test_state_loading_precedes_routing(self, mock_orchestrator_no_init):
        """Test state is loaded before routing decision."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_7, checkpoint="agents_written")

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_7') as mock_run:
            mock_run.return_value = Mock(success=True)
            result = mock_orchestrator_no_init.run()

            # State should be loaded first
            mock_orchestrator_no_init.state_manager.load_state.assert_called()
            # Then phase handler should be called
            mock_run.assert_called()

    def test_exception_handling_in_run(self, mock_orchestrator_no_init):
        """Test exception handling during resume."""
        mock_orchestrator_no_init.config.resume = True

        with patch.object(mock_orchestrator_no_init, 'state_manager') as mock_state_manager:
            mock_state_manager.load_state.side_effect = KeyboardInterrupt()

            result = mock_orchestrator_no_init.run()

            # Should return error result
            assert result.success is False

    def test_run_returns_orchestration_result(self, mock_orchestrator_no_init):
        """Test run() always returns OrchestrationResult."""
        mock_orchestrator_no_init.config.resume = True

        setup_mock_state_manager(mock_orchestrator_no_init, WorkflowPhase.PHASE_5)

        with patch.object(mock_orchestrator_no_init, '_run_from_phase_5') as mock_run:
            mock_run.return_value = Mock(
                success=True,
                template_name="test-template",
                output_path=Path("/home/user"),
                errors=[],
                warnings=[]
            )
            result = mock_orchestrator_no_init.run()

            # Should return a result object
            assert result is not None
            assert hasattr(result, 'success')


# ========== DRY Principle Tests ==========

class TestResumeRoutingDRY:
    """Test DRY principle in resume routing."""

    # REMOVED: test_phase_7_5_reuses_phase_7_logic (TASK-SIMP-9ABE)
    # Phase 7.5 has been removed entirely

    def test_centralizes_phase_routing(self, mock_orchestrator_no_init):
        """Test phase routing is centralized in run() method."""
        # Routing logic should be in one place (run method)
        # not duplicated across multiple methods
        assert hasattr(mock_orchestrator_no_init, 'run')

        # The run method should contain the explicit routing logic
        run_method = mock_orchestrator_no_init.run
        assert callable(run_method)


# ========== Edge Cases ==========

class TestResumeRoutingEdgeCases:
    """Test edge cases in resume routing."""

    # REMOVED: test_handles_floating_point_phase (TASK-SIMP-9ABE)
    # Phase 7.5 (float phase) has been removed
    # Still have Phase 4.5 and 9.5 for float phase support

    def test_handles_invalid_phase(self, mock_orchestrator_no_init):
        """Test handles invalid/unknown phase gracefully."""
        mock_orchestrator_no_init.config.resume = True

        with patch.object(mock_orchestrator_no_init, 'state_manager') as mock_state_manager:
            state = Mock()
            state.phase = 99  # Invalid phase
            mock_state_manager.load_state.return_value = state

            with patch.object(mock_orchestrator_no_init, '_run_from_phase_5') as mock_run:
                mock_run.return_value = Mock(success=True)
                result = mock_orchestrator_no_init.run()

                # Should fall back gracefully
                mock_run.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
