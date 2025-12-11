"""
Template Generator Module

This module provides AI-assisted generation of .template files from example code files.
It uses Claude Code integration to intelligently extract placeholders while preserving
code structure and patterns.

Core Components:
    - TemplateGenerator: Main orchestrator for template generation
    - AIClient: Integration with Claude for placeholder extraction
    - Template validation and deduplication utilities
    - Layer classification for template organization (TASK-FIX-40B4)

Layer Classification:
    - LayerClassificationOrchestrator: Coordinates JS-specific and generic classifiers
    - JavaScriptLayerClassifier: JavaScript/TypeScript folder convention patterns
    - GenericLayerClassifier: Cross-language fallback patterns
    - ClassificationResult: Result with confidence scoring

Usage:
    from lib.template_generator import TemplateGenerator
    from lib.codebase_analyzer import CodebaseAnalysis

    generator = TemplateGenerator(analysis)
    collection = generator.generate(max_templates=20)
    generator.save_templates(collection, output_dir)

    # For custom layer classification:
    from lib.template_generator import LayerClassificationOrchestrator
    orchestrator = LayerClassificationOrchestrator()
    result = orchestrator.classify(example_file, analysis)
"""

from .template_generator import TemplateGenerator
from .claude_md_generator import ClaudeMdGenerator
from .rules_structure_generator import RulesStructureGenerator, RuleFile
from .models import (
    CodeTemplate,
    TemplateCollection,
    ValidationResult,
    GenerationError,
    ValidationError,
    PlaceholderExtractionError,
    TemplateClaude,
    AgentMetadata
)
from .ai_client import AIClient, MockAIClient
from .layer_classifier import (
    LayerClassificationOrchestrator,
    JavaScriptLayerClassifier,
    GenericLayerClassifier,
    ClassificationResult,
    LayerClassificationStrategy
)

__all__ = [
    "TemplateGenerator",
    "ClaudeMdGenerator",
    "RulesStructureGenerator",
    "RuleFile",
    "CodeTemplate",
    "TemplateCollection",
    "ValidationResult",
    "GenerationError",
    "ValidationError",
    "PlaceholderExtractionError",
    "TemplateClaude",
    "AgentMetadata",
    "AIClient",
    "MockAIClient",
    # Layer classification exports (TASK-FIX-40B4)
    "LayerClassificationOrchestrator",
    "JavaScriptLayerClassifier",
    "GenericLayerClassifier",
    "ClassificationResult",
    "LayerClassificationStrategy",
]

__version__ = "0.1.0"
