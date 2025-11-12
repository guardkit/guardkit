"""
AI-Powered Codebase Analysis Module

This module provides intelligent analysis of codebases to extract architectural
patterns, technology stack information, and quality metrics. It integrates with
the architectural-reviewer agent for deep analysis and provides structured
output for template creation workflows.

Core Components:
    - CodebaseAnalyzer: Main orchestrator for codebase analysis
    - Models: Pydantic data models for structured analysis output
    - AgentInvoker: Communication layer for architectural-reviewer agent
    - PromptBuilder: Constructs context-aware prompts for agent invocation
    - ResponseParser: Parses and validates agent responses
    - AnalysisSerializer: Saves/loads analysis results

Usage:
    from lib.codebase_analyzer import CodebaseAnalyzer

    analyzer = CodebaseAnalyzer()
    analysis = analyzer.analyze_codebase(
        codebase_path="/path/to/project",
        template_context={"name": "FastAPI", "language": "python"}
    )

    # Access structured results
    print(f"Stack: {analysis.technology.primary_language}")
    print(f"Architecture: {analysis.architecture.patterns}")
    print(f"Quality Score: {analysis.quality.overall_score}")
"""

# Import using importlib to avoid 'global' keyword issue
import importlib

_ai_analyzer_module = importlib.import_module('lib.codebase_analyzer.ai_analyzer')
_models_module = importlib.import_module('lib.codebase_analyzer.models')
_serializer_module = importlib.import_module('lib.codebase_analyzer.serializer')

CodebaseAnalyzer = _ai_analyzer_module.CodebaseAnalyzer
analyze_codebase = _ai_analyzer_module.analyze_codebase
CodebaseAnalysis = _models_module.CodebaseAnalysis
TechnologyInfo = _models_module.TechnologyInfo
ArchitectureInfo = _models_module.ArchitectureInfo
QualityInfo = _models_module.QualityInfo
ExampleFile = _models_module.ExampleFile
LayerInfo = _models_module.LayerInfo
ConfidenceScore = _models_module.ConfidenceScore
ConfidenceLevel = _models_module.ConfidenceLevel
ParseError = _models_module.ParseError
AnalysisError = _models_module.AnalysisError
AnalysisSerializer = _serializer_module.AnalysisSerializer

__all__ = [
    "CodebaseAnalyzer",
    "analyze_codebase",
    "CodebaseAnalysis",
    "TechnologyInfo",
    "ArchitectureInfo",
    "QualityInfo",
    "ExampleFile",
    "LayerInfo",
    "ConfidenceScore",
    "ConfidenceLevel",
    "ParseError",
    "AnalysisError",
    "AnalysisSerializer",
]

__version__ = "0.1.0"
