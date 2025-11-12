"""
Template Generator Module

This module provides AI-assisted generation of .template files from example code files.
It uses Claude Code integration to intelligently extract placeholders while preserving
code structure and patterns.

Core Components:
    - TemplateGenerator: Main orchestrator for template generation
    - AIClient: Integration with Claude for placeholder extraction
    - Template validation and deduplication utilities

Usage:
    from lib.template_generator import TemplateGenerator
    from lib.codebase_analyzer import CodebaseAnalysis

    generator = TemplateGenerator(analysis)
    collection = generator.generate(max_templates=20)
    generator.save_templates(collection, output_dir)
"""

import importlib

# Import using importlib to avoid 'global' keyword issue
_template_generator_module = importlib.import_module('installer.global.lib.template_generator.template_generator')
_models_module = importlib.import_module('installer.global.lib.template_generator.models')
_ai_client_module = importlib.import_module('installer.global.lib.template_generator.ai_client')

TemplateGenerator = _template_generator_module.TemplateGenerator

CodeTemplate = _models_module.CodeTemplate
TemplateCollection = _models_module.TemplateCollection
ValidationResult = _models_module.ValidationResult
GenerationError = _models_module.GenerationError
ValidationError = _models_module.ValidationError
PlaceholderExtractionError = _models_module.PlaceholderExtractionError

AIClient = _ai_client_module.AIClient
MockAIClient = _ai_client_module.MockAIClient

__all__ = [
    "TemplateGenerator",
    "CodeTemplate",
    "TemplateCollection",
    "ValidationResult",
    "GenerationError",
    "ValidationError",
    "PlaceholderExtractionError",
    "AIClient",
    "MockAIClient",
]

__version__ = "0.1.0"
