"""
Settings Generator Module

Generates template settings.json from AI-powered codebase analysis.
"""

from lib.settings_generator.models import (
    CaseStyle,
    TestLocation,
    NamingConvention,
    FileOrganization,
    LayerMapping,
    CodeStyle,
    TemplateSettings,
    TemplateSettingsError,
    ValidationError,
    GenerationError
)

from lib.settings_generator.generator import SettingsGenerator
from lib.settings_generator.validator import TemplateSettingsValidator

__all__ = [
    # Models
    "CaseStyle",
    "TestLocation",
    "NamingConvention",
    "FileOrganization",
    "LayerMapping",
    "CodeStyle",
    "TemplateSettings",

    # Exceptions
    "TemplateSettingsError",
    "ValidationError",
    "GenerationError",

    # Core classes
    "SettingsGenerator",
    "TemplateSettingsValidator",
]

__version__ = "0.1.0"
