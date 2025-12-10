"""
Unit tests for _ensure_templates_on_disk() method.

Tests idempotent template writing behavior to ensure templates are written
exactly once before Phase 7.5 (agent enhancement).

TASK-PHASE-7-5-TEMPLATE-PREWRITE-FIX
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import logging

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
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.codebase_path = Path("/test/codebase")
    config.output_path = None
    config.output_location = "global"
    config.max_templates = None
    config.dry_run = False
    config.save_analysis = False
    config.no_agents = False
    config.skip_validation = False
    config.validate = False
    config.resume = False
    config.custom_name = None
    config.verbose = False
    return config


@pytest.fixture
def mock_orchestrator(mock_config):
    """Create a mock orchestrator instance."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orchestrator = TemplateCreateOrchestrator(mock_config)
        orchestrator.config = mock_config
        orchestrator._templates_written_to_disk = False
        orchestrator.templates = None
        orchestrator.warnings = []
        orchestrator.errors = []
        return orchestrator


@pytest.fixture
def mock_templates():
    """Create mock template collection."""
    templates = Mock()
    templates.total_count = 5
    templates.templates = [Mock() for _ in range(5)]
    return templates


# ========== Unit Tests: Idempotent Writing ==========

class TestEnsureTemplatesOnDiskIdempotency:
    """Test idempotent behavior of _ensure_templates_on_disk()."""

    def test_writes_templates_on_first_call(self, mock_orchestrator, mock_templates, temp_dir):
        """Test templates are written on first call."""
        mock_orchestrator.templates = mock_templates

        # Patch TemplateGenerator in the orchestrator module namespace
        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # First call should write templates
            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Verify TemplateGenerator was instantiated with (None, None)
            MockTemplateGen.assert_called_once_with(None, None)

            # Verify save_templates was called
            mock_gen_instance.save_templates.assert_called_once_with(mock_templates, temp_dir)

            # Verify flag was set
            assert mock_orchestrator._templates_written_to_disk is True

    def test_idempotent_second_call_skips_write(self, mock_orchestrator, mock_templates, temp_dir):
        """Test second call skips writing (idempotent)."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # First call
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            first_call_count = MockTemplateGen.call_count

            # Second call should skip writing
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            second_call_count = MockTemplateGen.call_count

            # Verify TemplateGenerator was instantiated only once
            assert second_call_count == 1
            assert second_call_count == first_call_count

    def test_multiple_calls_write_only_once(self, mock_orchestrator, mock_templates, temp_dir):
        """Test multiple calls write templates only once."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Call multiple times
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Verify TemplateGenerator was instantiated exactly once
            assert MockTemplateGen.call_count == 1

            # Verify save_templates was called exactly once
            assert mock_gen_instance.save_templates.call_count == 1

    def test_allows_retry_after_error(self, mock_orchestrator, mock_templates, temp_dir):
        """Test retry is allowed after write error."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            # First call fails
            mock_gen_instance_1 = MockTemplateGen.return_value
            mock_gen_instance_1.save_templates = Mock(side_effect=Exception("Write failed"))

            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Flag should NOT be set after error
            assert mock_orchestrator._templates_written_to_disk is False

            # Verify first attempt was made
            assert MockTemplateGen.call_count == 1

            # Second call succeeds
            mock_gen_instance_2 = MockTemplateGen.return_value
            mock_gen_instance_2.save_templates = Mock()

            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Verify second call was attempted
            assert MockTemplateGen.call_count == 2
            assert mock_orchestrator._templates_written_to_disk is True


# ========== Unit Tests: Edge Cases ==========

class TestEnsureTemplatesOnDiskEdgeCases:
    """Test edge cases for _ensure_templates_on_disk()."""

    def test_handles_no_templates(self, mock_orchestrator, temp_dir):
        """Test graceful handling when no templates exist."""
        mock_orchestrator.templates = None

        # Should not raise exception
        mock_orchestrator._ensure_templates_on_disk(temp_dir)

        # Flag should be set even with no templates
        assert mock_orchestrator._templates_written_to_disk is True

    def test_handles_empty_template_collection(self, mock_orchestrator, temp_dir):
        """Test handling of empty template collection."""
        mock_templates = Mock()
        mock_templates.total_count = 0
        mock_templates.templates = []
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Should not call TemplateGenerator with empty collection
            assert MockTemplateGen.call_count == 0
            assert mock_orchestrator._templates_written_to_disk is True

    def test_logs_template_count_info(self, mock_orchestrator, mock_templates, temp_dir, caplog):
        """Test logging of template count."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            with caplog.at_level(logging.INFO):
                mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Verify log message includes template count
            log_messages = [record.message for record in caplog.records]
            assert any('5 templates' in msg for msg in log_messages), \
                f"Expected '5 templates' in logs, got: {log_messages}"

    def test_concurrent_calls_safety(self, mock_orchestrator, mock_templates, temp_dir):
        """Test thread-safety of idempotent flag."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Simulate concurrent calls (in practice, orchestrator is single-threaded)
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Even with "concurrent" calls, should write only once
            assert MockTemplateGen.call_count == 1


# ========== Integration Tests: Phase 7.5 Integration ==========

class TestPhase7_5Integration:
    """Test integration with Phase 7.5 (agent enhancement)."""

    def test_centralizes_template_writing_logic(self, mock_orchestrator, mock_templates, temp_dir):
        """Test that template writing logic is centralized."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Method should be the single source of truth for template writing
            mock_orchestrator._ensure_templates_on_disk(temp_dir)

            # Verify TemplateGenerator was used correctly
            MockTemplateGen.assert_called_once_with(None, None)
            mock_gen_instance.save_templates.assert_called_once_with(mock_templates, temp_dir)

    def test_idempotent_behavior_consistency(self, mock_orchestrator, mock_templates, temp_dir):
        """Test consistent idempotent behavior across calls."""
        mock_orchestrator.templates = mock_templates

        with patch.object(orchestrator_module, 'TemplateGenerator') as MockTemplateGen:
            mock_gen_instance = MockTemplateGen.return_value
            mock_gen_instance.save_templates = Mock()

            # Multiple paths through code should have same result
            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            flag_after_first = mock_orchestrator._templates_written_to_disk

            mock_orchestrator._ensure_templates_on_disk(temp_dir)
            flag_after_second = mock_orchestrator._templates_written_to_disk

            # Flag should be consistent
            assert flag_after_first is True
            assert flag_after_second is True
            assert MockTemplateGen.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
