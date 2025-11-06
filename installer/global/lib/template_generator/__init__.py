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

from lib.template_generator.template_generator import TemplateGenerator
from lib.template_generator.models import (
    CodeTemplate,
    TemplateCollection,
    ValidationResult,
    GenerationError,
    ValidationError,
    PlaceholderExtractionError,
)
from lib.template_generator.ai_client import AIClient, MockAIClient

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
