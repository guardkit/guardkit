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

from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer, analyze_codebase
from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    ExampleFile,
    LayerInfo,
    ConfidenceScore,
)
from lib.codebase_analyzer.serializer import AnalysisSerializer

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
    "AnalysisSerializer",
]

__version__ = "0.1.0"
