"""
Tests for Template Config Handler

Tests config file I/O, validation, and error handling.

TASK-9038: Create /template-qa Command for Optional Customization
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from installer.core.lib.template_config_handler import (
    TemplateConfigHandler,
    ConfigValidationError
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory for config files."""
    return tmp_path


@pytest.fixture
def valid_config_data():
    """Return valid configuration data."""
    return {
        "template_name": "my-template",
        "template_purpose": "quick_start",
        "primary_language": "csharp",
        "framework": "maui",
        "framework_version": "latest",
        "architecture_pattern": "mvvm",
        "domain_modeling": "rich",
        "layer_organization": "single",
        "standard_folders": ["src", "tests"],
        "unit_testing_framework": "xunit",
        "testing_scope": ["unit", "integration"],
        "test_pattern": "aaa",
        "error_handling": "result",
        "validation_approach": "fluent",
        "dependency_injection": "builtin",
        "configuration_approach": "both",
        "description": "Test template",
        "version": "1.0.0",
        "author": "Test Author"
    }


@pytest.fixture
def config_handler(temp_config_dir):
    """Create config handler instance."""
    return TemplateConfigHandler(temp_config_dir)


class TestConfigSave:
    """Test config saving functionality."""

    def test_save_valid_config(self, config_handler, valid_config_data, temp_config_dir):
        """Test saving valid configuration."""
        config_file = config_handler.save_config(valid_config_data)

        assert config_file.exists()
        assert config_file == temp_config_dir / ".template-create-config.json"

        # Verify file content
        with open(config_file, 'r') as f:
            file_content = json.load(f)

        assert "version" in file_content
        assert "created_at" in file_content
        assert "updated_at" in file_content
        assert "config" in file_content
        assert file_content["config"] == valid_config_data

    def test_save_creates_directory(self, temp_config_dir, valid_config_data):
        """Test that save creates parent directory if needed."""
        nested_dir = temp_config_dir / "nested" / "path"
        handler = TemplateConfigHandler(nested_dir)

        config_file = handler.save_config(valid_config_data)

        assert config_file.exists()
        assert config_file.parent == nested_dir

    def test_save_invalid_config_raises_error(self, config_handler):
        """Test that saving invalid config raises error."""
        invalid_config = {"template_name": "test"}  # Missing required fields

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.save_config(invalid_config)

        assert "Missing required fields" in str(exc_info.value)

    def test_save_custom_path(self, temp_config_dir, valid_config_data):
        """Test saving to custom path."""
        custom_path = temp_config_dir / "custom"
        handler = TemplateConfigHandler()

        config_file = handler.save_config(valid_config_data, custom_path)

        assert config_file == custom_path / ".template-create-config.json"
        assert config_file.exists()


class TestConfigLoad:
    """Test config loading functionality."""

    def test_load_valid_config(self, config_handler, valid_config_data):
        """Test loading valid configuration."""
        # Save first
        config_handler.save_config(valid_config_data)

        # Load
        loaded_config = config_handler.load_config()

        assert loaded_config == valid_config_data

    def test_load_nonexistent_config_raises_error(self, config_handler):
        """Test that loading nonexistent config raises error."""
        with pytest.raises(FileNotFoundError):
            config_handler.load_config()

    def test_load_invalid_json_raises_error(self, config_handler, temp_config_dir):
        """Test that loading invalid JSON raises error."""
        # Create invalid JSON file
        config_file = temp_config_dir / ".template-create-config.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.load_config()

        assert "Invalid JSON" in str(exc_info.value)

    def test_load_missing_version_raises_error(self, config_handler, temp_config_dir, valid_config_data):
        """Test that loading config without version raises error."""
        # Create file without version
        config_file = temp_config_dir / ".template-create-config.json"
        config_file.write_text(json.dumps({"config": valid_config_data}))

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.load_config()

        assert "missing 'version' field" in str(exc_info.value)

    def test_load_missing_config_field_raises_error(self, config_handler, temp_config_dir):
        """Test that loading config without config field raises error."""
        # Create file without config
        config_file = temp_config_dir / ".template-create-config.json"
        config_file.write_text(json.dumps({"version": "1.0"}))

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.load_config()

        assert "missing 'config' field" in str(exc_info.value)

    def test_load_custom_path(self, temp_config_dir, valid_config_data):
        """Test loading from custom path."""
        custom_path = temp_config_dir / "custom"
        handler = TemplateConfigHandler()

        # Save to custom path
        handler.save_config(valid_config_data, custom_path)

        # Load from custom path
        loaded_config = handler.load_config(custom_path)

        assert loaded_config == valid_config_data


class TestConfigValidation:
    """Test config validation functionality."""

    def test_validate_valid_config(self, config_handler, valid_config_data):
        """Test validation of valid config."""
        # Should not raise any errors
        config_handler.validate_config(valid_config_data)

    def test_validate_missing_required_field(self, config_handler, valid_config_data):
        """Test validation fails for missing required field."""
        invalid_config = valid_config_data.copy()
        del invalid_config["template_name"]

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "template_name" in str(exc_info.value)

    def test_validate_invalid_template_name_length(self, config_handler, valid_config_data):
        """Test validation fails for invalid template name length."""
        # Too short
        invalid_config = valid_config_data.copy()
        invalid_config["template_name"] = "ab"

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "3-50 characters" in str(exc_info.value)

        # Too long
        invalid_config["template_name"] = "a" * 51

        with pytest.raises(ConfigValidationError):
            config_handler.validate_config(invalid_config)

    def test_validate_invalid_field_type(self, config_handler, valid_config_data):
        """Test validation fails for invalid field type."""
        invalid_config = valid_config_data.copy()
        invalid_config["template_name"] = 123  # Should be string

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "must be a string" in str(exc_info.value)

    def test_validate_invalid_list_type(self, config_handler, valid_config_data):
        """Test validation fails for invalid list type."""
        invalid_config = valid_config_data.copy()
        invalid_config["standard_folders"] = "not a list"

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "must be a list" in str(exc_info.value)

    def test_validate_empty_list(self, config_handler, valid_config_data):
        """Test validation fails for empty required list."""
        invalid_config = valid_config_data.copy()
        invalid_config["standard_folders"] = []

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "cannot be empty" in str(exc_info.value)

    def test_validate_invalid_version_format(self, config_handler, valid_config_data):
        """Test validation fails for invalid version format."""
        invalid_config = valid_config_data.copy()
        invalid_config["version"] = "not a version!!!"

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(invalid_config)

        assert "Invalid version format" in str(exc_info.value)

    def test_validate_optional_fields(self, config_handler, valid_config_data):
        """Test validation passes with optional fields."""
        config_with_optionals = valid_config_data.copy()
        config_with_optionals.update({
            "ui_architecture": "mvvm",
            "navigation_pattern": "shell",
            "needs_data_access": True,
            "data_access": "ef-core",
            "has_documentation": False
        })

        # Should not raise
        config_handler.validate_config(config_with_optionals)


class TestConfigUtilities:
    """Test config utility methods."""

    def test_config_exists_true(self, config_handler, valid_config_data):
        """Test config_exists returns True when file exists."""
        config_handler.save_config(valid_config_data)

        assert config_handler.config_exists() is True

    def test_config_exists_false(self, config_handler):
        """Test config_exists returns False when file doesn't exist."""
        assert config_handler.config_exists() is False

    def test_update_config(self, config_handler, valid_config_data):
        """Test updating existing config."""
        # Save initial config
        config_handler.save_config(valid_config_data)

        # Update
        updates = {
            "template_name": "updated-name",
            "version": "2.0.0"
        }
        config_handler.update_config(updates)

        # Load and verify
        updated_config = config_handler.load_config()

        assert updated_config["template_name"] == "updated-name"
        assert updated_config["version"] == "2.0.0"
        # Other fields unchanged
        assert updated_config["primary_language"] == valid_config_data["primary_language"]

    def test_update_nonexistent_config_raises_error(self, config_handler):
        """Test updating nonexistent config raises error."""
        with pytest.raises(FileNotFoundError):
            config_handler.update_config({"template_name": "test"})

    def test_get_config_summary(self, config_handler, valid_config_data):
        """Test getting config summary."""
        config_handler.save_config(valid_config_data)

        summary = config_handler.get_config_summary()

        assert "config_file" in summary
        assert summary["template_name"] == "my-template"
        assert summary["language"] == "csharp"
        assert summary["framework"] == "maui"
        assert summary["architecture"] == "mvvm"
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_get_config_summary_nonexistent_raises_error(self, config_handler):
        """Test getting summary of nonexistent config raises error."""
        with pytest.raises(FileNotFoundError):
            config_handler.get_config_summary()


class TestFieldTypeValidation:
    """Test detailed field type validation."""

    def test_validate_boolean_fields(self, config_handler, valid_config_data):
        """Test validation of boolean fields."""
        config = valid_config_data.copy()
        config["needs_data_access"] = "not a bool"

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(config)

        assert "must be a boolean" in str(exc_info.value)

    def test_validate_list_contents(self, config_handler, valid_config_data):
        """Test validation of list contents."""
        config = valid_config_data.copy()
        config["standard_folders"] = ["src", 123]  # Invalid: contains non-string

        with pytest.raises(ConfigValidationError) as exc_info:
            config_handler.validate_config(config)

        assert "must contain strings" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_save_with_permission_error(self, config_handler, valid_config_data, temp_config_dir, monkeypatch):
        """Test handling of permission errors during save."""
        # Make directory read-only (platform-dependent)
        import os
        if os.name != 'nt':  # Unix-like systems
            temp_config_dir.chmod(0o444)

            try:
                with pytest.raises(IOError):
                    config_handler.save_config(valid_config_data)
            finally:
                # Restore permissions for cleanup
                temp_config_dir.chmod(0o755)

    def test_load_with_read_error(self, config_handler, valid_config_data, temp_config_dir):
        """Test handling of read errors during load."""
        # Save valid config first
        config_file = config_handler.save_config(valid_config_data)

        # Make file unreadable (platform-dependent)
        import os
        if os.name != 'nt':  # Unix-like systems
            config_file.chmod(0o000)

            try:
                with pytest.raises(IOError):
                    config_handler.load_config()
            finally:
                # Restore permissions for cleanup
                config_file.chmod(0o644)

    def test_unicode_in_config(self, config_handler, valid_config_data):
        """Test handling of Unicode characters in config."""
        config = valid_config_data.copy()
        config["description"] = "Template with émojis 🚀 and ünïcödé"

        # Should save and load without errors
        config_handler.save_config(config)
        loaded = config_handler.load_config()

        assert loaded["description"] == config["description"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
