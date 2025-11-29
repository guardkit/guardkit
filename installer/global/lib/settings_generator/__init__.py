"""
Settings Generator Module

Generates template settings.json from AI-powered codebase analysis.
"""

import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('installer.global.lib.settings_generator.models')
_generator_module = importlib.import_module('installer.global.lib.settings_generator.generator')
_validator_module = importlib.import_module('installer.global.lib.settings_generator.validator')

CaseStyle = _models_module.CaseStyle
TestLocation = _models_module.TestLocation
NamingConvention = _models_module.NamingConvention
FileOrganization = _models_module.FileOrganization
LayerMapping = _models_module.LayerMapping
CodeStyle = _models_module.CodeStyle
TemplateSettings = _models_module.TemplateSettings
TemplateSettingsError = _models_module.TemplateSettingsError
ValidationError = _models_module.ValidationError
GenerationError = _models_module.GenerationError

SettingsGenerator = _generator_module.SettingsGenerator
TemplateSettingsValidator = _validator_module.TemplateSettingsValidator

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
