"""
Template Settings Validator

Validates TemplateSettings for correctness and completeness.
"""

from typing import List, Optional
import importlib

from pydantic import ValidationError as PydanticValidationError

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('installer.global.lib.settings_generator.models')

TemplateSettings = _models_module.TemplateSettings
CaseStyle = _models_module.CaseStyle
TestLocation = _models_module.TestLocation
ValidationError = _models_module.ValidationError


class ValidationResult:
    """Result of validation."""

    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None,
                 warnings: Optional[List[str]] = None):
        """Initialize validation result.

        Args:
            is_valid: Whether validation passed
            errors: List of error messages
            warnings: List of warning messages
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __repr__(self) -> str:
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


class TemplateSettingsValidator:
    """Validate TemplateSettings.

    Example:
        validator = TemplateSettingsValidator()
        result = validator.validate(settings)
        if not result.is_valid:
            print(f"Errors: {result.errors}")
    """

    VALID_CASE_STYLES = [style.value for style in CaseStyle]
    VALID_TEST_LOCATIONS = [loc.value for loc in TestLocation]

    def validate(self, settings: TemplateSettings) -> ValidationResult:
        """Validate template settings.

        Args:
            settings: TemplateSettings to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Validate using Pydantic first
        try:
            # This will raise if the model is invalid
            settings.model_validate(settings.model_dump())
        except PydanticValidationError as e:
            errors.append(f"Pydantic validation failed: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Schema version
        if not settings.schema_version:
            errors.append("schema_version is required")
        elif settings.schema_version != "1.0.0":
            warnings.append(f"Unexpected schema_version: {settings.schema_version}")

        # Naming conventions
        if not settings.naming_conventions:
            errors.append("naming_conventions is required and must not be empty")
        else:
            for key, conv in settings.naming_conventions.items():
                # Validate case style (Pydantic should handle this, but double-check)
                # Note: use_enum_values=True means these are already strings, not enum objects
                case_style_value = conv.case_style if isinstance(conv.case_style, str) else conv.case_style.value
                if case_style_value not in self.VALID_CASE_STYLES:
                    errors.append(f"Invalid case_style in {key}: {conv.case_style}")

                # Validate pattern has content
                if not conv.pattern or not conv.pattern.strip():
                    errors.append(f"Empty pattern in naming convention: {key}")

                # Warn if no examples
                if not conv.examples:
                    warnings.append(f"No examples provided for naming convention: {key}")

        # File organization
        if not settings.file_organization:
            errors.append("file_organization is required")
        else:
            # Validate test location
            # Note: use_enum_values=True means these are already strings, not enum objects
            test_loc_value = settings.file_organization.test_location if isinstance(settings.file_organization.test_location, str) else settings.file_organization.test_location.value
            if test_loc_value not in self.VALID_TEST_LOCATIONS:
                errors.append(
                    f"Invalid test_location: {settings.file_organization.test_location}"
                )

            # Warn if both by_layer and by_feature are False
            if not settings.file_organization.by_layer and not settings.file_organization.by_feature:
                warnings.append(
                    "Neither by_layer nor by_feature organization is enabled"
                )

            # Validate max_files_per_directory if set
            if settings.file_organization.max_files_per_directory is not None:
                if settings.file_organization.max_files_per_directory < 1:
                    errors.append("max_files_per_directory must be at least 1")
                elif settings.file_organization.max_files_per_directory < 10:
                    warnings.append(
                        f"Low max_files_per_directory: "
                        f"{settings.file_organization.max_files_per_directory}"
                    )

        # Layer mappings
        if not settings.layer_mappings:
            warnings.append("No layer_mappings defined")
        else:
            for layer_name, mapping in settings.layer_mappings.items():
                # Validate directory is not empty
                if not mapping.directory or not mapping.directory.strip():
                    errors.append(f"Empty directory in layer mapping: {layer_name}")

                # Validate name matches key
                if mapping.name != layer_name:
                    warnings.append(
                        f"Layer mapping key '{layer_name}' doesn't match "
                        f"name '{mapping.name}'"
                    )

                # Warn if no file patterns
                if not mapping.file_patterns:
                    warnings.append(f"No file_patterns for layer: {layer_name}")

        # Code style (optional, but validate if present)
        if settings.code_style:
            # Validate indentation
            if settings.code_style.indentation not in ["spaces", "tabs"]:
                errors.append(
                    f"Invalid indentation: {settings.code_style.indentation}. "
                    f"Must be 'spaces' or 'tabs'"
                )

            # Validate indent_size (Pydantic should handle range, but double-check)
            if settings.code_style.indent_size < 1 or settings.code_style.indent_size > 8:
                errors.append(
                    f"Invalid indent_size: {settings.code_style.indent_size}. "
                    f"Must be 1-8"
                )

            # Validate line_length if set
            if settings.code_style.line_length is not None:
                if settings.code_style.line_length < 40:
                    warnings.append(
                        f"Very short line_length: {settings.code_style.line_length}"
                    )
                elif settings.code_style.line_length > 200:
                    warnings.append(
                        f"Very long line_length: {settings.code_style.line_length}"
                    )

        # Generation options (optional, minimal validation)
        if settings.generation_options:
            # Just warn if it's empty
            if not settings.generation_options:
                warnings.append("generation_options is empty")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_compatibility(self, settings: TemplateSettings,
                               language: str) -> ValidationResult:
        """Validate settings are compatible with a specific language.

        Args:
            settings: TemplateSettings to validate
            language: Target language (e.g., "Python", "C#", "TypeScript")

        Returns:
            ValidationResult with compatibility errors/warnings
        """
        errors = []
        warnings = []

        lang_lower = language.lower()

        # Check namespace patterns are appropriate for language
        for layer_name, mapping in settings.layer_mappings.items():
            if mapping.namespace_pattern:
                # Languages that don't use namespaces
                if lang_lower in ["python", "javascript"]:
                    warnings.append(
                        f"Layer '{layer_name}' has namespace_pattern but "
                        f"{language} doesn't use namespaces"
                    )

                # Languages that require namespaces
                if lang_lower in ["c#", "csharp", "java", "kotlin"]:
                    if not mapping.namespace_pattern:
                        warnings.append(
                            f"Layer '{layer_name}' missing namespace_pattern "
                            f"for {language}"
                        )

        # Check file patterns match language
        for layer_name, mapping in settings.layer_mappings.items():
            if mapping.file_patterns:
                has_correct_extension = any(
                    self._matches_language_extension(pattern, lang_lower)
                    for pattern in mapping.file_patterns
                )

                if not has_correct_extension:
                    warnings.append(
                        f"Layer '{layer_name}' file_patterns may not match "
                        f"{language} files"
                    )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _matches_language_extension(self, pattern: str, language: str) -> bool:
        """Check if file pattern matches language extension."""
        # Map languages to extensions
        lang_extensions = {
            "python": [".py"],
            "c#": [".cs"],
            "csharp": [".cs"],
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "java": [".java"],
            "kotlin": [".kt"],
        }

        extensions = lang_extensions.get(language, [])
        return any(ext in pattern for ext in extensions)
