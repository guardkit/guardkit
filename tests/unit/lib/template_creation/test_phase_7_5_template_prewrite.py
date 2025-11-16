"""
Unit tests for TASK-PHASE-7-5-TEMPLATE-PREWRITE-FIX implementation.

Tests the following changes:
1. _templates_written_to_disk flag tracking
2. _ensure_templates_on_disk() idempotent method
3. Integration with _complete_workflow (normal flow)
4. Integration with _run_from_phase_7 (resume flow)

Coverage targets: ≥80% line coverage, ≥75% branch coverage
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import sys
import importlib.util
import logging

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


# ========== Test Fixtures ==========

@pytest.fixture
def mock_config():
    """Create mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.codebase_path = Path("/test/codebase")
    config.output_path = None
    config.output_location = "global"
    config.dry_run = False
    config.resume = False
    config.verbose = False
    return config


@pytest.fixture
def orchestrator(mock_config):
    """Create orchestrator instance with mocked dependencies."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orch = TemplateCreateOrchestrator(mock_config)
        orch.config = mock_config
        orch.errors = []
        orch.warnings = []
        orch._templates_written_to_disk = False  # Initialize flag
        return orch


@pytest.fixture
def orchestrator_with_templates(orchestrator):
    """Create orchestrator with mock templates collection."""
    orchestrator.templates = Mock()
    orchestrator.templates.total_count = 5
    orchestrator.templates.templates = [Mock(), Mock(), Mock(), Mock(), Mock()]
    return orchestrator


@pytest.fixture
def orchestrator_with_workflow_data(orchestrator_with_templates):
    """Create orchestrator with all workflow data needed for _complete_workflow."""
    orchestrator_with_templates.manifest = Mock()
    orchestrator_with_templates.manifest.name = "test-template"

    orchestrator_with_templates.settings = Mock()
    orchestrator_with_templates.analysis = Mock()
    orchestrator_with_templates.agents = [Mock(name="agent1"), Mock(name="agent2")]

    return orchestrator_with_templates


# ========== Unit Tests: Flag Initialization ==========

class TestTemplatesWrittenToDiskFlag:
    """Test _templates_written_to_disk flag initialization and behavior."""

    def test_flag_initialized_to_false(self, mock_config):
        """Flag should be initialized to False on orchestrator creation."""
        with patch.object(TemplateCreateOrchestrator, '_resume_from_checkpoint'):
            orch = TemplateCreateOrchestrator(mock_config)
            assert orch._templates_written_to_disk is False

    def test_flag_persists_across_calls(self, orchestrator):
        """Flag should persist its state across method calls."""
        # Set flag
        orchestrator._templates_written_to_disk = True

        # Verify persistence
        assert orchestrator._templates_written_to_disk is True

        # Call another method that might access it
        orchestrator._templates_written_to_disk = False
        assert orchestrator._templates_written_to_disk is False

    def test_flag_independent_per_instance(self, mock_config):
        """Each orchestrator instance should have independent flag state."""
        with patch.object(TemplateCreateOrchestrator, '_resume_from_checkpoint'):
            orch1 = TemplateCreateOrchestrator(mock_config)
            orch2 = TemplateCreateOrchestrator(mock_config)

            orch1._templates_written_to_disk = True
            orch2._templates_written_to_disk = False

            assert orch1._templates_written_to_disk is True
            assert orch2._templates_written_to_disk is False


# ========== Unit Tests: _ensure_templates_on_disk() Method ==========

class TestEnsureTemplatesOnDisk:
    """Test _ensure_templates_on_disk() idempotent method."""

    def test_skips_if_already_written(self, orchestrator_with_templates):
        """Should skip writing if flag is already True (idempotent behavior)."""
        # Set flag to True
        orchestrator_with_templates._templates_written_to_disk = True

        with patch('commands.lib.template_create_orchestrator.TemplateGenerator') as MockGen:
            orchestrator_with_templates._ensure_templates_on_disk(Path('/tmp/output'))

            # TemplateGenerator should NOT be instantiated
            MockGen.assert_not_called()

    def test_skips_if_no_templates_none(self, orchestrator):
        """Should skip if templates is None."""
        orchestrator.templates = None

        with patch('commands.lib.template_create_orchestrator.TemplateGenerator') as MockGen:
            orchestrator._ensure_templates_on_disk(Path('/tmp/output'))

            # Should not attempt to write
            MockGen.assert_not_called()

            # Flag should be set to prevent retry
            assert orchestrator._templates_written_to_disk is True

    def test_skips_if_templates_empty(self, orchestrator):
        """Should skip if templates collection has zero count."""
        orchestrator.templates = Mock()
        orchestrator.templates.total_count = 0

        with patch('commands.lib.template_create_orchestrator.TemplateGenerator') as MockGen:
            orchestrator._ensure_templates_on_disk(Path('/tmp/output'))

            # Should not write
            MockGen.assert_not_called()

            # Flag should be set
            assert orchestrator._templates_written_to_disk is True

    def test_writes_templates_on_first_call(self, orchestrator_with_templates):
        """Should write templates to disk on first call."""
        output_path = Path('/tmp/output')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            orchestrator_with_templates._ensure_templates_on_disk(output_path)

            # _write_templates_to_disk should be called with correct arguments
            mock_write.assert_called_once_with(
                orchestrator_with_templates.templates,
                output_path
            )

            # Flag should be set
            assert orchestrator_with_templates._templates_written_to_disk is True

    def test_idempotent_second_call_skips_write(self, orchestrator_with_templates):
        """Should NOT write templates on second call (idempotent)."""
        output_path = Path('/tmp/output')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            # First call - should write
            orchestrator_with_templates._ensure_templates_on_disk(output_path)
            assert mock_write.call_count == 1

            # Second call - should skip
            orchestrator_with_templates._ensure_templates_on_disk(output_path)
            assert mock_write.call_count == 1  # Still only 1

    def test_multiple_calls_write_only_once(self, orchestrator_with_templates):
        """Should only write once even with multiple calls."""
        output_path = Path('/tmp/output')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            # Call multiple times
            for _ in range(5):
                orchestrator_with_templates._ensure_templates_on_disk(output_path)

            # Should only write once
            assert mock_write.call_count == 1

    def test_handles_write_error_gracefully(self, orchestrator_with_templates, caplog):
        """Should handle write errors without crashing."""
        caplog.set_level(logging.WARNING)
        output_path = Path('/tmp/output')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=False) as mock_write:
            # Should not raise exception
            orchestrator_with_templates._ensure_templates_on_disk(output_path)

            # Flag should NOT be set on error (allows retry)
            assert orchestrator_with_templates._templates_written_to_disk is False

            # Should log warning
            assert "Failed to pre-write templates" in caplog.text

    def test_allows_retry_after_error(self, orchestrator_with_templates):
        """Should allow retry after error (flag not set)."""
        output_path = Path('/tmp/output')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk') as mock_write:
            # First call fails
            mock_write.return_value = False
            orchestrator_with_templates._ensure_templates_on_disk(output_path)
            assert orchestrator_with_templates._templates_written_to_disk is False

            # Second call succeeds
            mock_write.return_value = True
            orchestrator_with_templates._ensure_templates_on_disk(output_path)

            # Should have been called twice
            assert mock_write.call_count == 2
            assert orchestrator_with_templates._templates_written_to_disk is True

    def test_logs_template_count_info(self, orchestrator_with_templates, caplog):
        """Should log information about template count."""
        caplog.set_level(logging.INFO)

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True):
            orchestrator_with_templates._ensure_templates_on_disk(Path('/tmp/output'))

            # Check log messages
            assert "Writing 5 templates to disk" in caplog.text
            assert "Successfully wrote 5 template files" in caplog.text

    def test_logs_skip_when_already_written(self, orchestrator_with_templates, caplog):
        """Should log debug message when skipping."""
        caplog.set_level(logging.DEBUG)
        orchestrator_with_templates._templates_written_to_disk = True

        orchestrator_with_templates._ensure_templates_on_disk(Path('/tmp/output'))

        assert "Templates already written to disk, skipping" in caplog.text

    def test_logs_skip_when_no_templates(self, orchestrator, caplog):
        """Should log debug message when no templates."""
        caplog.set_level(logging.DEBUG)
        orchestrator.templates = None

        orchestrator._ensure_templates_on_disk(Path('/tmp/output'))

        assert "No templates to write to disk" in caplog.text


# ========== Integration Tests: _complete_workflow ==========

class TestCompleteWorkflowIntegration:
    """Test integration with _complete_workflow method."""

    def test_calls_ensure_templates_before_phase_7_5(self, orchestrator_with_workflow_data):
        """Should call _ensure_templates_on_disk before Phase 7.5."""
        with patch.object(orchestrator_with_workflow_data, '_phase7_write_agents',
                         return_value=[Path('agent1.md'), Path('agent2.md')]), \
             patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_with_workflow_data, '_save_checkpoint'), \
             patch.object(orchestrator_with_workflow_data, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # _ensure_templates_on_disk should be called once
            assert mock_ensure.call_count == 1

    def test_skips_ensure_if_no_agents(self, orchestrator_with_workflow_data):
        """Should skip _ensure_templates_on_disk if no agents exist."""
        orchestrator_with_workflow_data.agents = []

        with patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # Should not be called
            mock_ensure.assert_not_called()

    def test_skips_ensure_if_agent_write_fails(self, orchestrator_with_workflow_data):
        """Should skip _ensure_templates_on_disk if agent writing fails."""
        with patch.object(orchestrator_with_workflow_data, '_phase7_write_agents',
                         return_value=None), \
             patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # Should not be called
            mock_ensure.assert_not_called()

    def test_execution_order_write_ensure_enhance(self, orchestrator_with_workflow_data):
        """Should execute in order: write agents → ensure templates → enhance agents."""
        call_order = []

        def track_write_agents(*args, **kwargs):
            call_order.append('write_agents')
            return [Path('agent1.md')]

        def track_ensure(*args, **kwargs):
            call_order.append('ensure_templates')

        def track_enhance(*args, **kwargs):
            call_order.append('enhance_agents')
            return True

        with patch.object(orchestrator_with_workflow_data, '_phase7_write_agents',
                         side_effect=track_write_agents), \
             patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk',
                         side_effect=track_ensure), \
             patch.object(orchestrator_with_workflow_data, '_save_checkpoint'), \
             patch.object(orchestrator_with_workflow_data, '_phase7_5_enhance_agents',
                         side_effect=track_enhance), \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # Verify execution order
            assert call_order == ['write_agents', 'ensure_templates', 'enhance_agents']

    def test_passes_correct_output_path_global(self, orchestrator_with_workflow_data):
        """Should pass correct output path (global location)."""
        orchestrator_with_workflow_data.config.output_path = None
        orchestrator_with_workflow_data.config.output_location = 'global'

        expected_path = Path.home() / ".agentecflow" / "templates" / "test-template"

        with patch.object(orchestrator_with_workflow_data, '_phase7_write_agents',
                         return_value=[Path('agent1.md')]), \
             patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_with_workflow_data, '_save_checkpoint'), \
             patch.object(orchestrator_with_workflow_data, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # Check path argument
            mock_ensure.assert_called_once_with(expected_path)

    def test_passes_correct_output_path_repo(self, orchestrator_with_workflow_data):
        """Should pass correct output path (repo location)."""
        orchestrator_with_workflow_data.config.output_path = None
        orchestrator_with_workflow_data.config.output_location = 'repo'

        expected_path = Path("installer/global/templates") / "test-template"

        with patch.object(orchestrator_with_workflow_data, '_phase7_write_agents',
                         return_value=[Path('agent1.md')]), \
             patch.object(orchestrator_with_workflow_data, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_with_workflow_data, '_save_checkpoint'), \
             patch.object(orchestrator_with_workflow_data, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_with_workflow_data, '_complete_workflow_from_phase_8'):

            orchestrator_with_workflow_data._complete_workflow()

            # Check path argument
            mock_ensure.assert_called_once_with(expected_path)


# ========== Integration Tests: _run_from_phase_7 (Resume Flow) ==========

class TestRunFromPhase7Integration:
    """Test integration with _run_from_phase_7 resume workflow."""

    @pytest.fixture
    def orchestrator_resume(self, mock_config):
        """Create orchestrator for resume testing."""
        mock_config.resume = True

        with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
            orch = TemplateCreateOrchestrator(mock_config)
            orch.config = mock_config
            orch._templates_written_to_disk = False

            orch.manifest = Mock()
            orch.manifest.name = "test-template"

            orch.templates = Mock()
            orch.templates.total_count = 3

            orch.agents = [Mock(name="agent1")]

            return orch

    def test_calls_ensure_on_resume(self, orchestrator_resume):
        """Should call _ensure_templates_on_disk when resuming from Phase 7."""
        with patch.object(orchestrator_resume, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_resume, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_resume, '_complete_workflow_from_phase_8'):

            orchestrator_resume._run_from_phase_7()

            # Should be called once
            assert mock_ensure.call_count == 1

    def test_resume_execution_order(self, orchestrator_resume):
        """Should execute in order: ensure templates → enhance agents → complete workflow."""
        call_order = []

        def track_ensure(*args, **kwargs):
            call_order.append('ensure_templates')

        def track_enhance(*args, **kwargs):
            call_order.append('enhance_agents')
            return True

        def track_complete(*args, **kwargs):
            call_order.append('complete_workflow')

        with patch.object(orchestrator_resume, '_ensure_templates_on_disk',
                         side_effect=track_ensure), \
             patch.object(orchestrator_resume, '_phase7_5_enhance_agents',
                         side_effect=track_enhance), \
             patch.object(orchestrator_resume, '_complete_workflow_from_phase_8',
                         side_effect=track_complete):

            try:
                orchestrator_resume._run_from_phase_7()
            except:
                pass  # May fail due to mocked return values

            # Verify order
            assert call_order == ['ensure_templates', 'enhance_agents', 'complete_workflow']

    def test_resume_passes_output_path_global(self, orchestrator_resume):
        """Should calculate and pass correct global output path on resume."""
        orchestrator_resume.config.output_path = None
        orchestrator_resume.config.output_location = 'global'

        expected_path = Path.home() / ".agentecflow" / "templates" / "test-template"

        with patch.object(orchestrator_resume, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_resume, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_resume, '_complete_workflow_from_phase_8'):

            orchestrator_resume._run_from_phase_7()

            mock_ensure.assert_called_once_with(expected_path)

    def test_resume_passes_output_path_repo(self, orchestrator_resume):
        """Should calculate and pass correct repo output path on resume."""
        orchestrator_resume.config.output_path = None
        orchestrator_resume.config.output_location = 'repo'

        expected_path = Path("installer/global/templates") / "test-template"

        with patch.object(orchestrator_resume, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_resume, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_resume, '_complete_workflow_from_phase_8'):

            orchestrator_resume._run_from_phase_7()

            mock_ensure.assert_called_once_with(expected_path)

    def test_resume_uses_custom_output_path(self, orchestrator_resume):
        """Should use custom output path if provided."""
        custom_path = Path("/custom/output/path")
        orchestrator_resume.config.output_path = custom_path

        with patch.object(orchestrator_resume, '_ensure_templates_on_disk') as mock_ensure, \
             patch.object(orchestrator_resume, '_phase7_5_enhance_agents', return_value=True), \
             patch.object(orchestrator_resume, '_complete_workflow_from_phase_8'):

            orchestrator_resume._run_from_phase_7()

            mock_ensure.assert_called_once_with(custom_path)


# ========== Edge Case Tests ==========

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_templates_attribute_missing_total_count(self, orchestrator):
        """Should handle templates object without total_count attribute."""
        orchestrator.templates = Mock(spec=['templates'])  # Missing total_count

        with pytest.raises(AttributeError):
            orchestrator._ensure_templates_on_disk(Path('/tmp/output'))

    def test_templates_total_count_zero_vs_none(self, orchestrator):
        """Should distinguish between total_count=0 and templates=None."""
        # Case 1: templates is None
        orchestrator.templates = None
        with patch('commands.lib.template_create_orchestrator.TemplateGenerator') as MockGen:
            orchestrator._ensure_templates_on_disk(Path('/tmp/output'))
            MockGen.assert_not_called()
            assert orchestrator._templates_written_to_disk is True

        # Reset flag
        orchestrator._templates_written_to_disk = False

        # Case 2: total_count is 0
        orchestrator.templates = Mock()
        orchestrator.templates.total_count = 0
        with patch('commands.lib.template_create_orchestrator.TemplateGenerator') as MockGen:
            orchestrator._ensure_templates_on_disk(Path('/tmp/output'))
            MockGen.assert_not_called()
            assert orchestrator._templates_written_to_disk is True

    def test_concurrent_calls_safety(self, orchestrator_with_templates):
        """Test behavior with rapid sequential calls (basic concurrency check)."""
        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            # Simulate rapid calls
            for _ in range(10):
                orchestrator_with_templates._ensure_templates_on_disk(Path('/tmp/output'))

            # Should only write once
            assert mock_write.call_count == 1


# ========== DRY Improvement Tests ==========

class TestDRYImprovement:
    """Test that _ensure_templates_on_disk improves code reuse (DRY)."""

    def test_centralizes_template_writing_logic(self, orchestrator_with_templates):
        """Verify method centralizes template writing logic."""
        output_path = Path('/tmp/test')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            # Call from method
            orchestrator_with_templates._ensure_templates_on_disk(output_path)

            # Verify consistent behavior
            mock_write.assert_called_once_with(
                orchestrator_with_templates.templates,
                output_path
            )

    def test_idempotent_behavior_consistency(self, orchestrator_with_templates):
        """Verify idempotent behavior is consistent across calls."""
        output_path = Path('/tmp/test')

        with patch.object(orchestrator_with_templates, '_write_templates_to_disk', return_value=True) as mock_write:
            # First call
            orchestrator_with_templates._ensure_templates_on_disk(output_path)
            first_call_count = mock_write.call_count

            # Second call
            orchestrator_with_templates._ensure_templates_on_disk(output_path)
            second_call_count = mock_write.call_count

            # Verify idempotency
            assert first_call_count == 1
            assert second_call_count == 1  # Should still be 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=commands.lib.template_create_orchestrator",
                 "--cov-report=term-missing", "--cov-report=json"])
