"""
Template Config Handler

Handles loading, saving, and validation of .template-create-config.json files.
Provides config persistence for /template-qa command.

TASK-9038: Create /template-qa Command for Optional Customization
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .state_paths import get_state_file, TEMPLATE_CONFIG


class ConfigValidationError(Exception):
    """Raised when config validation fails."""
    pass


class TemplateConfigHandler:
    """
    Handles template configuration file operations.

    Config file: .template-create-config.json (project root)
    Format: JSON mirroring GreenfieldAnswers dataclass

    Usage:
        handler = TemplateConfigHandler()

        # Save config
        config_data = answers.to_dict()
        handler.save_config(config_data, Path("."))

        # Load config
        config = handler.load_config(Path("."))

        # Validate config
        handler.validate_config(config)
    """

    CONFIG_FILENAME = ".template-create-config.json"
    CONFIG_VERSION = "1.0"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config handler.

        Args:
            config_path: Optional path to config file directory (default: ~/.agentecflow/state/)
        """
        if config_path is not None:
            # Explicit path provided - use it (backwards compatibility)
            self.config_dir = config_path
            self.config_file = self.config_dir / self.CONFIG_FILENAME
        else:
            # Default to state directory (TASK-FIX-STATE02)
            self.config_file = get_state_file(TEMPLATE_CONFIG)
            self.config_dir = self.config_file.parent

    def save_config(
        self,
        config_data: Dict[str, Any],
        config_path: Optional[Path] = None
    ) -> Path:
        """
        Save configuration to file.

        Args:
            config_data: Configuration dictionary (from GreenfieldAnswers.to_dict())
            config_path: Optional override for config directory

        Returns:
            Path to saved config file

        Raises:
            ConfigValidationError: If config data is invalid
            IOError: If file write fails
        """
        # Validate before saving
        self.validate_config(config_data)

        # Determine output path
        if config_path:
            config_file = config_path / self.CONFIG_FILENAME
        else:
            config_file = self.config_file

        # Build file content with metadata
        file_content = {
            "version": self.CONFIG_VERSION,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "config": config_data
        }

        # Write to file
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(file_content, f, indent=2, ensure_ascii=False)
            return config_file
        except Exception as e:
            raise IOError(f"Failed to save config file: {e}")

    def load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_path: Optional override for config directory

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If config is invalid
            IOError: If file read fails
        """
        # Determine config file path
        if config_path:
            config_file = config_path / self.CONFIG_FILENAME
        else:
            config_file = self.config_file

        # Check file exists
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Read file
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read config file: {e}")

        # Validate file structure
        if "version" not in file_content:
            raise ConfigValidationError("Config file missing 'version' field")

        if "config" not in file_content:
            raise ConfigValidationError("Config file missing 'config' field")

        # Check version compatibility
        if file_content["version"] != self.CONFIG_VERSION:
            # Log warning but continue (forward compatibility)
            print(f"Warning: Config version mismatch (file: {file_content['version']}, expected: {self.CONFIG_VERSION})")

        config_data = file_content["config"]

        # Validate config data
        self.validate_config(config_data)

        return config_data

    def config_exists(self, config_path: Optional[Path] = None) -> bool:
        """
        Check if config file exists.

        Args:
            config_path: Optional override for config directory

        Returns:
            True if config file exists, False otherwise
        """
        if config_path:
            config_file = config_path / self.CONFIG_FILENAME
        else:
            config_file = self.config_file

        return config_file.exists()

    def update_config(
        self,
        updates: Dict[str, Any],
        config_path: Optional[Path] = None
    ) -> Path:
        """
        Update existing config file with new values.

        Args:
            updates: Dictionary of fields to update
            config_path: Optional override for config directory

        Returns:
            Path to updated config file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If updated config is invalid
        """
        # Load existing config
        existing_config = self.load_config(config_path)

        # Merge updates
        existing_config.update(updates)

        # Save updated config
        return self.save_config(existing_config, config_path)

    def validate_config(self, config_data: Dict[str, Any]) -> None:
        """
        Validate configuration data.

        Args:
            config_data: Configuration dictionary to validate

        Raises:
            ConfigValidationError: If validation fails
        """
        # Required fields (from GreenfieldAnswers)
        required_fields = [
            "template_name",
            "template_purpose",
            "primary_language",
            "framework",
            "framework_version",
            "architecture_pattern",
            "domain_modeling",
            "layer_organization",
            "standard_folders",
            "unit_testing_framework",
            "testing_scope",
            "test_pattern",
            "error_handling",
            "validation_approach",
            "dependency_injection",
            "configuration_approach"
        ]

        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in config_data:
                missing_fields.append(field)

        if missing_fields:
            raise ConfigValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        self._validate_field_types(config_data)

        # Validate field values
        self._validate_field_values(config_data)

    def _validate_field_types(self, config_data: Dict[str, Any]) -> None:
        """
        Validate field types.

        Args:
            config_data: Configuration dictionary

        Raises:
            ConfigValidationError: If type validation fails
        """
        # String fields
        string_fields = [
            "template_name", "template_purpose", "primary_language",
            "framework", "framework_version", "architecture_pattern",
            "domain_modeling", "layer_organization", "unit_testing_framework",
            "test_pattern", "error_handling", "validation_approach",
            "dependency_injection", "configuration_approach"
        ]

        for field in string_fields:
            if field in config_data and not isinstance(config_data[field], str):
                raise ConfigValidationError(
                    f"Field '{field}' must be a string, got {type(config_data[field]).__name__}"
                )

        # List fields
        list_fields = ["standard_folders", "testing_scope"]

        for field in list_fields:
            if field in config_data:
                if not isinstance(config_data[field], list):
                    raise ConfigValidationError(
                        f"Field '{field}' must be a list, got {type(config_data[field]).__name__}"
                    )
                # Validate list contents are strings
                for item in config_data[field]:
                    if not isinstance(item, str):
                        raise ConfigValidationError(
                            f"Field '{field}' must contain strings, found {type(item).__name__}"
                        )

        # Optional string fields
        optional_string_fields = [
            "description", "version", "author", "ui_architecture",
            "navigation_pattern", "data_access", "api_pattern",
            "state_management", "documentation_input_method",
            "documentation_text", "documentation_usage"
        ]

        for field in optional_string_fields:
            if field in config_data and config_data[field] is not None:
                if not isinstance(config_data[field], str):
                    raise ConfigValidationError(
                        f"Field '{field}' must be a string or null, got {type(config_data[field]).__name__}"
                    )

        # Optional boolean fields
        optional_bool_fields = ["needs_data_access", "has_documentation"]

        for field in optional_bool_fields:
            if field in config_data and config_data[field] is not None:
                if not isinstance(config_data[field], bool):
                    raise ConfigValidationError(
                        f"Field '{field}' must be a boolean or null, got {type(config_data[field]).__name__}"
                    )

        # Optional list fields
        optional_list_fields = ["documentation_paths", "documentation_urls"]

        for field in optional_list_fields:
            if field in config_data and config_data[field] is not None:
                if not isinstance(config_data[field], list):
                    raise ConfigValidationError(
                        f"Field '{field}' must be a list or null, got {type(config_data[field]).__name__}"
                    )

    def _validate_field_values(self, config_data: Dict[str, Any]) -> None:
        """
        Validate field values.

        Args:
            config_data: Configuration dictionary

        Raises:
            ConfigValidationError: If value validation fails
        """
        # Validate template_name format
        template_name = config_data.get("template_name", "")
        if not template_name or len(template_name) < 3 or len(template_name) > 50:
            raise ConfigValidationError(
                "template_name must be 3-50 characters"
            )

        # Validate version format if present
        if "version" in config_data and config_data["version"]:
            version = config_data["version"]
            # Simple semantic version check
            if not version.replace('.', '').replace('-', '').isalnum():
                raise ConfigValidationError(
                    f"Invalid version format: {version}"
                )

        # Validate non-empty lists
        for field in ["standard_folders", "testing_scope"]:
            if field in config_data:
                if not config_data[field]:
                    raise ConfigValidationError(
                        f"Field '{field}' cannot be empty"
                    )

    def get_config_summary(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get summary of config file contents.

        Args:
            config_path: Optional override for config directory

        Returns:
            Dictionary with config summary

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        # Determine config file path
        if config_path:
            config_file = config_path / self.CONFIG_FILENAME
        else:
            config_file = self.config_file

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Read file
        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)

        config_data = file_content.get("config", {})

        return {
            "config_file": str(config_file),
            "version": file_content.get("version", "unknown"),
            "created_at": file_content.get("created_at", "unknown"),
            "updated_at": file_content.get("updated_at", "unknown"),
            "template_name": config_data.get("template_name", "unknown"),
            "language": config_data.get("primary_language", "unknown"),
            "framework": config_data.get("framework", "unknown"),
            "architecture": config_data.get("architecture_pattern", "unknown")
        }


# Module exports
__all__ = [
    "TemplateConfigHandler",
    "ConfigValidationError"
]
