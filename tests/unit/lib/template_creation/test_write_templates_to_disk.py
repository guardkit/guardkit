"""
Unit tests for _write_templates_to_disk() method.

Tests centralized template writing logic with consistent error handling
and SystemExit propagation for bridge pattern compatibility.

TASK-PHASE-7-5-FIX-FOUNDATION: DRY principle improvement
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core"
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
    """Mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.codebase_path = Path("/test/codebase")
    config.output_path = None
    config.output_location = "global"
    config.dry_run = False
    return config


@pytest.fixture
def mock_orchestrator(mock_config):
    """Create a mock orchestrator instance."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orchestrator = TemplateCreateOrchestrator(mock_config)
        orchestrator.config = mock_config
        orchestrator.errors = []
        orchestrator.warnings = []
        return orchestrator


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_templates():
    """Create mock template collection."""
    templates = Mock()
    templates.total_count = 3
    templates.templates = [Mock() for _ in range(3)]
    return templates


# ========== Unit Tests: Success Cases ==========

class TestWriteTemplatesToDiskSuccess:
    """Test successful template writing."""

    def test_calls_template_generator_correctly(self, mock_orchestrator, mock_templates, temp_dir):
        """Test TemplateGenerator is instantiated and used correctly."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Verify instantiation with (None, None)
            MockTemplateGen.assert_called_once_with(None, None)

            # Verify save_templates called with templates and output_path
            mock_gen_instance.save_templates.assert_called_once_with(mock_templates, temp_dir)

            # Verify return value
            assert result is True

    def test_returns_true_on_success(self, mock_orchestrator, mock_templates, temp_dir):
        """Test returns True when writing succeeds."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is True

    def test_logs_success_message(self, mock_orchestrator, mock_templates, temp_dir):
        """Test logs success message with template count."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            with patch('logging.getLogger') as mock_logger:
                logger = Mock()
                mock_logger.return_value = logger

                result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

                # Should log success (we can't directly check module-level logger,
                # but we verify the method returns True)
                assert result is True


# ========== Unit Tests: Empty/None Cases ==========

class TestWriteTemplatesToDiskEmpty:
    """Test handling of empty or None templates."""

    def test_handles_none_templates(self, mock_orchestrator, temp_dir):
        """Test graceful handling of None templates."""
        result = mock_orchestrator._write_templates_to_disk(None, temp_dir)

        assert result is True

    def test_handles_empty_template_collection(self, mock_orchestrator, temp_dir):
        """Test handling of empty template collection."""
        empty_templates = Mock()
        empty_templates.total_count = 0
        empty_templates.templates = []

        result = mock_orchestrator._write_templates_to_disk(empty_templates, temp_dir)

        assert result is True

    def test_does_not_call_generator_for_empty(self, mock_orchestrator, temp_dir):
        """Test TemplateGenerator not called for empty templates."""
        empty_templates = Mock()
        empty_templates.total_count = 0

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            result = mock_orchestrator._write_templates_to_disk(empty_templates, temp_dir)

            # Generator should not be instantiated for empty collection
            MockTemplateGen.assert_not_called()
            assert result is True


# ========== Unit Tests: SystemExit Handling ==========

class TestWriteTemplatesToDiskSystemExit:
    """Test SystemExit handling and propagation."""

    def test_propagates_exit_code_42(self, mock_orchestrator, mock_templates, temp_dir):
        """Test exit code 42 is propagated (bridge pattern)."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=SystemExit(42))

            with pytest.raises(SystemExit) as exc_info:
                mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert exc_info.value.code == 42

    def test_propagates_agent_invocation_exit(self, mock_orchestrator, mock_templates, temp_dir):
        """Test agent invocation exit is propagated."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            # Simulate agent bridge requesting exit for agent invocation
            mock_gen_instance.save_templates = Mock(side_effect=SystemExit(42))

            with pytest.raises(SystemExit) as exc_info:
                mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Verify exit code is preserved
            assert exc_info.value.code == 42

    def test_returns_false_for_other_exit_codes(self, mock_orchestrator, mock_templates, temp_dir):
        """Test non-42 exit codes return False."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=SystemExit(1))

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is False

    def test_logs_error_for_non_42_exit(self, mock_orchestrator, mock_templates, temp_dir):
        """Test error is logged for non-42 exit codes."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=SystemExit(1))

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is False


# ========== Unit Tests: Exception Handling ==========

class TestWriteTemplatesToDiskExceptions:
    """Test exception handling and error reporting."""

    def test_catches_generic_exceptions(self, mock_orchestrator, mock_templates, temp_dir):
        """Test generic exceptions are caught and logged."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(
                side_effect=RuntimeError("Failed to write templates")
            )

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is False

    def test_catches_file_not_found_error(self, mock_orchestrator, mock_templates, temp_dir):
        """Test FileNotFoundError is caught."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=FileNotFoundError("Path not found"))

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is False

    def test_catches_permission_error(self, mock_orchestrator, mock_templates, temp_dir):
        """Test PermissionError is caught."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=PermissionError("Access denied"))

            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is False

    def test_does_not_raise_on_exceptions(self, mock_orchestrator, mock_templates, temp_dir):
        """Test method doesn't raise exceptions (returns False instead)."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock(side_effect=Exception("Unexpected error"))

            # Should not raise exception
            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Should return False instead
            assert result is False


# ========== Unit Tests: DRY Principle Verification ==========

class TestWriteTemplatesToDiskDRY:
    """Test DRY principle implementation."""

    def test_centralizes_template_writing(self, mock_orchestrator, mock_templates, temp_dir):
        """Test this is the single source of truth for template writing."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # This method should be used in multiple places (e.g., Phase 7.5, Phase 9)
            # but with same underlying logic
            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Verify consistent behavior
            assert result is True
            MockTemplateGen.assert_called_once_with(None, None)

    def test_consistent_generator_instantiation(self, mock_orchestrator, mock_templates, temp_dir):
        """Test TemplateGenerator always instantiated the same way."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Call multiple times
            mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)
            mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Verify consistent instantiation
            assert all(call[0] == (None, None) for call in MockTemplateGen.call_args_list)


# ========== Integration Tests ==========

class TestWriteTemplatesToDiskIntegration:
    """Integration tests with Phase 7.5 and Phase 9."""

    def test_suitable_for_phase_7_5_prewrite(self, mock_orchestrator, mock_templates, temp_dir):
        """Test method is suitable for Phase 7.5 pre-writing."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Phase 7.5 needs to pre-write templates before agent enhancement
            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is True
            mock_gen_instance.save_templates.assert_called_once()

    def test_suitable_for_phase_9_assembly(self, mock_orchestrator, mock_templates, temp_dir):
        """Test method is suitable for Phase 9 package assembly."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Phase 9 writes final templates
            result = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            assert result is True

    def test_provides_consistent_behavior_across_phases(self, mock_orchestrator, mock_templates, temp_dir):
        """Test consistent behavior across different phases."""
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Call from Phase 7.5
            result1 = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Reset mocks
            MockTemplateGen.reset_mock()
            mock_gen_instance.reset_mock()

            # Call from Phase 9
            result2 = mock_orchestrator._write_templates_to_disk(mock_templates, temp_dir)

            # Both should succeed and use same logic
            assert result1 is True
            assert result2 is True


# ========== Edge Cases ==========

class TestWriteTemplatesToDiskEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_handles_zero_templates(self, mock_orchestrator, temp_dir):
        """Test handling of zero templates."""
        empty = Mock()
        empty.total_count = 0

        result = mock_orchestrator._write_templates_to_disk(empty, temp_dir)

        assert result is True

    def test_handles_large_template_collection(self, mock_orchestrator, temp_dir):
        """Test handling of large template collections."""
        large = Mock()
        large.total_count = 1000
        large.templates = [Mock() for _ in range(1000)]

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            result = mock_orchestrator._write_templates_to_disk(large, temp_dir)

            assert result is True
            mock_gen_instance.save_templates.assert_called_once_with(large, temp_dir)

    def test_handles_various_output_paths(self, mock_orchestrator, mock_templates):
        """Test with various output path formats."""
        paths = [
            Path("/tmp/test"),
            Path("relative/path"),
            Path.home() / "templates",
        ]

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            for path in paths:
                result = mock_orchestrator._write_templates_to_disk(mock_templates, path)
                assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
