"""
Unit tests for _get_output_path() method.

Tests centralized output path determination logic across all 3 path modes:
- Explicit path (config.output_path)
- Repository location (config.output_location == 'repo')
- Global location (default, ~/.agentecflow/templates/)

TASK-PHASE-7-5-FIX-FOUNDATION: DRY principle improvement
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
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


# ========== Test Fixtures ==========

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
        orchestrator.manifest = None
        return orchestrator


@pytest.fixture
def mock_manifest():
    """Create mock manifest."""
    manifest = Mock()
    manifest.name = "my-template"
    manifest.language = "python"
    manifest.confidence_score = 85
    return manifest


# ========== Unit Tests: Path Priority ==========

class TestGetOutputPathPriority:
    """Test path priority order."""

    def test_explicit_path_takes_priority(self, mock_orchestrator, mock_manifest):
        """Test explicit path has highest priority."""
        mock_orchestrator.manifest = mock_manifest
        explicit_path = Path("/explicit/custom/path")
        mock_orchestrator.config.output_path = explicit_path

        result = mock_orchestrator._get_output_path()

        assert result == explicit_path

    def test_repo_location_when_no_explicit_path(self, mock_orchestrator, mock_manifest):
        """Test repo location used when output_path is None."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        result = mock_orchestrator._get_output_path()

        expected = Path("installer/global/templates/my-template")
        assert result == expected

    def test_global_location_default(self, mock_orchestrator, mock_manifest):
        """Test global location is default."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'global'

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/home/user")

            result = mock_orchestrator._get_output_path()

            expected = Path("/home/user/.agentecflow/templates/my-template")
            assert result == expected


# ========== Unit Tests: Manifest Validation ==========

class TestGetOutputPathManifestValidation:
    """Test manifest validation before path determination."""

    def test_raises_error_when_manifest_missing(self, mock_orchestrator):
        """Test error raised when manifest not generated."""
        mock_orchestrator.manifest = None

        with pytest.raises(ValueError) as exc_info:
            mock_orchestrator._get_output_path()

        assert "Manifest must be generated" in str(exc_info.value)

    def test_error_message_is_clear(self, mock_orchestrator):
        """Test error message provides clear guidance."""
        mock_orchestrator.manifest = None

        with pytest.raises(ValueError) as exc_info:
            mock_orchestrator._get_output_path()

        error_msg = str(exc_info.value)
        assert "before determining output path" in error_msg


# ========== Unit Tests: Template Name Handling ==========

class TestGetOutputPathTemplateNames:
    """Test template name handling in paths."""

    def test_includes_manifest_name_in_path(self, mock_orchestrator, mock_manifest):
        """Test manifest name is included in output path."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        result = mock_orchestrator._get_output_path()

        assert "my-template" in str(result)

    def test_handles_complex_template_names(self, mock_orchestrator, mock_manifest):
        """Test complex template names with special characters."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.manifest.name = "my-api-v2-templates"
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        result = mock_orchestrator._get_output_path()

        assert "my-api-v2-templates" in str(result)

    def test_different_template_names_produce_different_paths(self, mock_orchestrator, mock_manifest):
        """Test different template names produce different paths."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        # First template
        path1 = mock_orchestrator._get_output_path()

        # Change template name
        mock_orchestrator.manifest.name = "other-template"
        path2 = mock_orchestrator._get_output_path()

        assert path1 != path2
        assert "my-template" in str(path1)
        assert "other-template" in str(path2)


# ========== Unit Tests: Path Construction ==========

class TestGetOutputPathConstruction:
    """Test path construction logic."""

    def test_global_path_uses_home_directory(self, mock_orchestrator, mock_manifest):
        """Test global path includes home directory."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'global'

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/home/testuser")

            result = mock_orchestrator._get_output_path()

            assert str(result).startswith("/home/testuser")

    def test_repo_path_uses_relative_location(self, mock_orchestrator, mock_manifest):
        """Test repo path is relative."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        result = mock_orchestrator._get_output_path()

        # Check it starts with installer, not absolute path
        assert str(result).startswith("installer")
        assert not str(result).startswith("/")

    def test_explicit_path_returned_as_is(self, mock_orchestrator, mock_manifest):
        """Test explicit path is returned without modification."""
        mock_orchestrator.manifest = mock_manifest
        explicit = Path("/my/custom/path/my-template")
        mock_orchestrator.config.output_path = explicit

        result = mock_orchestrator._get_output_path()

        assert result == explicit
        # Manifest name should not be appended to explicit path
        assert result.name == "my-template"  # It's the last component


# ========== Unit Tests: Output Location Values ==========

class TestGetOutputPathLocationValues:
    """Test different output location values."""

    @pytest.mark.parametrize("location,should_be_repo", [
        ('repo', True),
        ('global', False),
        ('REPO', False),  # Case matters
        ('Global', False),
    ])
    def test_location_value_handling(self, mock_orchestrator, mock_manifest, location, should_be_repo):
        """Test different location value handling."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = location

        if location == 'repo':
            result = mock_orchestrator._get_output_path()
            assert "installer/global/templates" in str(result)
        else:
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path("/home/user")
                result = mock_orchestrator._get_output_path()
                assert ".agentecflow" in str(result)


# ========== Unit Tests: Edge Cases ==========

class TestGetOutputPathEdgeCases:
    """Test edge cases."""

    def test_single_call_consistency(self, mock_orchestrator, mock_manifest):
        """Test same manifest produces same path on multiple calls."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        result1 = mock_orchestrator._get_output_path()
        result2 = mock_orchestrator._get_output_path()

        assert result1 == result2

    def test_works_with_pathlib_path_objects(self, mock_orchestrator, mock_manifest):
        """Test that Path objects are handled correctly."""
        mock_orchestrator.manifest = mock_manifest

        # Explicit path as Path object
        explicit = Path("/tmp/test")
        mock_orchestrator.config.output_path = explicit

        result = mock_orchestrator._get_output_path()

        assert isinstance(result, Path)
        assert result == explicit


# ========== Integration Tests ==========

class TestGetOutputPathIntegration:
    """Integration tests with Phase 7.5 and other phases."""

    def test_provides_path_for_agent_enhancement(self, mock_orchestrator, mock_manifest):
        """Test path is suitable for agent enhancement in Phase 7.5."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'repo'

        output_path = mock_orchestrator._get_output_path()

        # Should include 'templates' directory component
        assert "templates" in str(output_path)
        assert mock_manifest.name in str(output_path)

    def test_consistent_with_write_templates_to_disk(self, mock_orchestrator, mock_manifest):
        """Test path is consistent with _write_templates_to_disk expectations."""
        mock_orchestrator.manifest = mock_manifest
        mock_orchestrator.config.output_path = None
        mock_orchestrator.config.output_location = 'global'

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/home/user")

            output_path = mock_orchestrator._get_output_path()

            # Path should be suitable for parent.mkdir(parents=True, exist_ok=True)
            assert isinstance(output_path, Path)
            # Should have parent directory
            assert output_path.parent != output_path


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
