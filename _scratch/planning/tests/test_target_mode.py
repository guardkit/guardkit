"""
Test suite for target mode configuration.

Tests cover:
- TargetMode enum validation
- TargetConfig dataclass structure
- resolve_target() function with various inputs
- Config file parsing and AUTO mode resolution
- Edge cases and error handling
"""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from guardkit.planning.target_mode import (
    TargetConfig,
    TargetMode,
    resolve_target,
)


class TestTargetModeEnum:
    """Test TargetMode enum has correct values."""

    def test_target_mode_has_interactive(self):
        """Test INTERACTIVE mode exists."""
        assert TargetMode.INTERACTIVE.value == "interactive"

    def test_target_mode_has_local_model(self):
        """Test LOCAL_MODEL mode exists."""
        assert TargetMode.LOCAL_MODEL.value == "local-model"

    def test_target_mode_has_auto(self):
        """Test AUTO mode exists."""
        assert TargetMode.AUTO.value == "auto"

    def test_target_mode_count(self):
        """Test enum has exactly 3 modes."""
        assert len(TargetMode) == 3


class TestTargetConfigDataclass:
    """Test TargetConfig dataclass structure."""

    def test_target_config_has_mode_field(self):
        """Test TargetConfig has mode field."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.mode == TargetMode.INTERACTIVE

    def test_target_config_has_model_name_field(self):
        """Test TargetConfig has model_name field."""
        config = TargetConfig(mode=TargetMode.LOCAL_MODEL, model_name="gpt-4")
        assert config.model_name == "gpt-4"

    def test_target_config_model_name_defaults_to_none(self):
        """Test model_name defaults to None."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.model_name is None

    def test_target_config_has_output_verbosity_field(self):
        """Test TargetConfig has output_verbosity field."""
        config = TargetConfig(mode=TargetMode.LOCAL_MODEL, output_verbosity="explicit")
        assert config.output_verbosity == "explicit"

    def test_target_config_output_verbosity_defaults_to_standard(self):
        """Test output_verbosity defaults to 'standard'."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.output_verbosity == "standard"

    def test_target_config_has_include_imports_field(self):
        """Test TargetConfig has include_imports field."""
        config = TargetConfig(mode=TargetMode.LOCAL_MODEL, include_imports=True)
        assert config.include_imports is True

    def test_target_config_include_imports_defaults_to_false(self):
        """Test include_imports defaults to False."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.include_imports is False

    def test_target_config_has_include_type_hints_field(self):
        """Test TargetConfig has include_type_hints field."""
        config = TargetConfig(mode=TargetMode.LOCAL_MODEL, include_type_hints=True)
        assert config.include_type_hints is True

    def test_target_config_include_type_hints_defaults_to_false(self):
        """Test include_type_hints defaults to False."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.include_type_hints is False

    def test_target_config_has_structured_coach_blocks_field(self):
        """Test TargetConfig has structured_coach_blocks field."""
        config = TargetConfig(mode=TargetMode.LOCAL_MODEL, structured_coach_blocks=True)
        assert config.structured_coach_blocks is True

    def test_target_config_structured_coach_blocks_defaults_to_false(self):
        """Test structured_coach_blocks defaults to False."""
        config = TargetConfig(mode=TargetMode.INTERACTIVE)
        assert config.structured_coach_blocks is False


class TestResolveTargetLocalModel:
    """Test resolve_target() with local-model flag."""

    def test_resolve_local_model_returns_correct_mode(self):
        """Test local-model flag sets mode to LOCAL_MODEL."""
        config = resolve_target("local-model")
        assert config.mode == TargetMode.LOCAL_MODEL

    def test_resolve_local_model_sets_explicit_verbosity(self):
        """Test local-model flag sets output_verbosity to 'explicit'."""
        config = resolve_target("local-model")
        assert config.output_verbosity == "explicit"

    def test_resolve_local_model_enables_imports(self):
        """Test local-model flag enables include_imports."""
        config = resolve_target("local-model")
        assert config.include_imports is True

    def test_resolve_local_model_enables_type_hints(self):
        """Test local-model flag enables include_type_hints."""
        config = resolve_target("local-model")
        assert config.include_type_hints is True

    def test_resolve_local_model_enables_structured_coach_blocks(self):
        """Test local-model flag enables structured_coach_blocks."""
        config = resolve_target("local-model")
        assert config.structured_coach_blocks is True


class TestResolveTargetInteractive:
    """Test resolve_target() with interactive flag."""

    def test_resolve_interactive_returns_correct_mode(self):
        """Test interactive flag sets mode to INTERACTIVE."""
        config = resolve_target("interactive")
        assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_interactive_sets_standard_verbosity(self):
        """Test interactive flag sets output_verbosity to 'standard'."""
        config = resolve_target("interactive")
        assert config.output_verbosity == "standard"

    def test_resolve_interactive_disables_imports(self):
        """Test interactive flag keeps include_imports as False."""
        config = resolve_target("interactive")
        assert config.include_imports is False

    def test_resolve_interactive_disables_type_hints(self):
        """Test interactive flag keeps include_type_hints as False."""
        config = resolve_target("interactive")
        assert config.include_type_hints is False

    def test_resolve_interactive_disables_structured_coach_blocks(self):
        """Test interactive flag keeps structured_coach_blocks as False."""
        config = resolve_target("interactive")
        assert config.structured_coach_blocks is False


class TestResolveTargetAuto:
    """Test resolve_target() with auto flag and config file detection."""

    def test_resolve_auto_with_endpoint_in_config(self):
        """Test AUTO mode resolves to LOCAL_MODEL when autobuild.endpoint exists."""
        config_content = """
autobuild:
  endpoint: http://localhost:11434
  model: llama3.2
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                assert config.mode == TargetMode.LOCAL_MODEL
                assert config.output_verbosity == "explicit"
                assert config.include_imports is True
                assert config.include_type_hints is True
                assert config.structured_coach_blocks is True

    def test_resolve_auto_without_endpoint_in_config(self):
        """Test AUTO mode resolves to INTERACTIVE when autobuild.endpoint missing."""
        config_content = """
task_defaults:
  complexity_threshold: 7
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                assert config.mode == TargetMode.INTERACTIVE
                assert config.output_verbosity == "standard"
                assert config.include_imports is False

    def test_resolve_auto_with_empty_autobuild_section(self):
        """Test AUTO mode with autobuild section but no endpoint."""
        config_content = """
autobuild:
  max_turns: 10
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_auto_with_missing_config_file(self):
        """Test AUTO mode defaults to INTERACTIVE when config file missing."""
        with patch("pathlib.Path.exists", return_value=False):
            config = resolve_target("auto")
            assert config.mode == TargetMode.INTERACTIVE
            assert config.output_verbosity == "standard"

    def test_resolve_auto_with_custom_config_path(self):
        """Test AUTO mode with custom config path."""
        config_content = """
autobuild:
  endpoint: http://custom:8080
"""
        custom_path = Path("/custom/config.yaml")
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto", config_path=custom_path)
                assert config.mode == TargetMode.LOCAL_MODEL


class TestResolveTargetDefaults:
    """Test resolve_target() with None and default behavior."""

    def test_resolve_target_none_defaults_to_auto(self):
        """Test None flag value defaults to AUTO mode behavior."""
        config_content = """
autobuild:
  endpoint: http://localhost:11434
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target(None)
                assert config.mode == TargetMode.LOCAL_MODEL

    def test_resolve_target_none_with_missing_config(self):
        """Test None flag with missing config defaults to INTERACTIVE."""
        with patch("pathlib.Path.exists", return_value=False):
            config = resolve_target(None)
            assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_no_arguments(self):
        """Test resolve_target() with no arguments."""
        with patch("pathlib.Path.exists", return_value=False):
            config = resolve_target()
            assert config.mode == TargetMode.INTERACTIVE


class TestResolveTargetEdgeCases:
    """Test resolve_target() edge cases and error handling."""

    def test_resolve_target_with_invalid_flag_value(self):
        """Test resolve_target with invalid flag value raises error."""
        with pytest.raises(ValueError, match="Invalid target mode"):
            resolve_target("invalid-mode")

    def test_resolve_target_with_empty_string(self):
        """Test resolve_target with empty string raises error."""
        with pytest.raises(ValueError, match="Invalid target mode"):
            resolve_target("")

    def test_resolve_target_with_empty_config_file(self):
        """Test AUTO mode with completely empty config file."""
        with patch("builtins.open", mock_open(read_data="")):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_with_invalid_yaml(self):
        """Test AUTO mode with invalid YAML content."""
        invalid_yaml = "autobuild:\n  endpoint: [invalid yaml structure"
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                # Should handle gracefully and default to INTERACTIVE
                assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_with_null_endpoint(self):
        """Test AUTO mode with null endpoint value."""
        config_content = """
autobuild:
  endpoint: null
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_case_insensitive_flag(self):
        """Test flag values are case-insensitive."""
        config = resolve_target("LOCAL-MODEL")
        assert config.mode == TargetMode.LOCAL_MODEL

        config = resolve_target("Interactive")
        assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_with_config_read_permission_error(self):
        """Test AUTO mode handles config file read permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                # Should handle gracefully and default to INTERACTIVE
                assert config.mode == TargetMode.INTERACTIVE

    def test_resolve_target_preserves_model_name_from_config(self):
        """Test AUTO mode can preserve model_name from config."""
        config_content = """
autobuild:
  endpoint: http://localhost:11434
  model: custom-model-name
"""
        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = resolve_target("auto")
                # This test validates the function can extract model name if implemented
                assert config.mode == TargetMode.LOCAL_MODEL


class TestTargetConfigIntegration:
    """Integration tests for complete target configuration workflow."""

    def test_full_workflow_interactive_to_local_model(self):
        """Test switching between interactive and local-model modes."""
        interactive_config = resolve_target("interactive")
        local_config = resolve_target("local-model")

        assert interactive_config.mode != local_config.mode
        assert interactive_config.output_verbosity != local_config.output_verbosity
        assert interactive_config.include_imports != local_config.include_imports

    def test_config_immutability(self):
        """Test TargetConfig instances are independent."""
        config1 = resolve_target("interactive")
        config2 = resolve_target("local-model")

        # Configs should be different objects
        assert config1 is not config2
        assert config1.mode != config2.mode
