"""
Pydantic Data Models for Codebase Analysis

Provides structured data models for representing codebase analysis results
including technology stack, architecture patterns, quality metrics, and
confidence scores.

These models follow the architectural review recommendations:
- Split CodebaseAnalysis into sub-models (SRP)
- Use clear type hints for validation
- Include confidence scores for AI-generated insights
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ConfidenceLevel(str, Enum):
    """Confidence level for analysis results."""
    HIGH = "high"      # 90-100% confidence
    MEDIUM = "medium"  # 70-89% confidence
    LOW = "low"        # 50-69% confidence
    UNCERTAIN = "uncertain"  # <50% confidence


class ConfidenceScore(BaseModel):
    """Confidence score with optional explanation."""
    level: ConfidenceLevel
    percentage: float = Field(ge=0.0, le=100.0)
    reasoning: Optional[str] = None

    @model_validator(mode='after')
    def validate_level_matches_percentage(self):
        """Ensure confidence level matches percentage."""
        percentage = self.percentage
        level = self.level

        if percentage >= 90 and level != ConfidenceLevel.HIGH:
            raise ValueError("High percentage (>=90) requires HIGH confidence level")
        if 70 <= percentage < 90 and level != ConfidenceLevel.MEDIUM:
            raise ValueError("Medium percentage (70-89) requires MEDIUM confidence level")
        if 50 <= percentage < 70 and level != ConfidenceLevel.LOW:
            raise ValueError("Low percentage (50-69) requires LOW confidence level")
        if percentage < 50 and level != ConfidenceLevel.UNCERTAIN:
            raise ValueError("Very low percentage (<50) requires UNCERTAIN confidence level")

        return self


class TechnologyInfo(BaseModel):
    """Technology stack information."""
    primary_language: str = Field(description="Primary programming language")
    frameworks: List[str] = Field(default_factory=list, description="Web frameworks, API frameworks, etc.")
    testing_frameworks: List[str] = Field(default_factory=list, description="Testing tools (pytest, jest, etc.)")
    build_tools: List[str] = Field(default_factory=list, description="Build/package managers")
    databases: List[str] = Field(default_factory=list, description="Database technologies")
    infrastructure: List[str] = Field(default_factory=list, description="Infrastructure tools (Docker, K8s, etc.)")
    confidence: ConfidenceScore


class LayerInfo(BaseModel):
    """Information about an architectural layer."""
    name: str = Field(description="Layer name (e.g., 'Domain', 'Application', 'Infrastructure')")
    description: str = Field(description="Purpose of this layer")
    typical_files: List[str] = Field(default_factory=list, description="Example file patterns")
    dependencies: List[str] = Field(default_factory=list, description="Allowed dependencies on other layers")


class ArchitectureInfo(BaseModel):
    """Architecture and design pattern information."""
    patterns: List[str] = Field(default_factory=list, description="Design patterns (Repository, Factory, etc.)")
    architectural_style: str = Field(description="Overall style (Layered, Clean Architecture, etc.)")
    layers: List[LayerInfo] = Field(default_factory=list, description="Architectural layers")
    key_abstractions: List[str] = Field(default_factory=list, description="Core domain abstractions")
    dependency_flow: str = Field(description="Direction of dependencies (e.g., 'Inward toward domain')")
    confidence: ConfidenceScore


class QualityInfo(BaseModel):
    """Quality metrics and assessment."""
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall quality score (0-100)")
    solid_compliance: float = Field(ge=0.0, le=100.0, description="SOLID principles compliance")
    dry_compliance: float = Field(ge=0.0, le=100.0, description="DRY (Don't Repeat Yourself) compliance")
    yagni_compliance: float = Field(ge=0.0, le=100.0, description="YAGNI (You Ain't Gonna Need It) compliance")
    test_coverage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Test coverage percentage if available")
    code_smells: List[str] = Field(default_factory=list, description="Identified code smells")
    strengths: List[str] = Field(default_factory=list, description="Architectural strengths")
    improvements: List[str] = Field(default_factory=list, description="Suggested improvements")
    confidence: ConfidenceScore


class ExampleFile(BaseModel):
    """Example file from the codebase."""
    path: str = Field(description="Relative path to file")
    purpose: str = Field(description="Purpose/role of this file")
    layer: Optional[str] = Field(None, description="Architectural layer")
    patterns_used: List[str] = Field(default_factory=list, description="Design patterns in this file")
    key_concepts: List[str] = Field(default_factory=list, description="Key concepts demonstrated")


class CodebaseAnalysis(BaseModel):
    """Complete codebase analysis result.

    Following architectural review recommendations, this is split into
    sub-models for technology, architecture, and quality (SRP).
    """
    codebase_path: str = Field(description="Path to analyzed codebase")
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # Sub-models (recommended by architectural review for SRP)
    technology: TechnologyInfo
    architecture: ArchitectureInfo
    quality: QualityInfo

    # Additional context
    example_files: List[ExampleFile] = Field(default_factory=list, description="Representative files")
    template_context: Optional[Dict[str, str]] = Field(None, description="Context from template creation")
    agent_used: bool = Field(default=False, description="Whether architectural-reviewer agent was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback if agent not used")

    # Metadata
    analysis_version: str = Field(default="0.1.0", description="Version of analysis module")

    @property
    def overall_confidence(self) -> ConfidenceScore:
        """Calculate overall confidence from sub-scores."""
        avg_percentage = (
            self.technology.confidence.percentage +
            self.architecture.confidence.percentage +
            self.quality.confidence.percentage
        ) / 3

        if avg_percentage >= 90:
            level = ConfidenceLevel.HIGH
        elif avg_percentage >= 70:
            level = ConfidenceLevel.MEDIUM
        elif avg_percentage >= 50:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.UNCERTAIN

        return ConfidenceScore(
            level=level,
            percentage=round(avg_percentage, 2),
            reasoning="Average of technology, architecture, and quality confidence scores"
        )

    def get_summary(self) -> str:
        """Get a human-readable summary of the analysis."""
        return f"""
Codebase Analysis Summary
========================
Path: {self.codebase_path}
Analyzed: {self.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}

Technology Stack:
  Language: {self.technology.primary_language}
  Frameworks: {', '.join(self.technology.frameworks) or 'None detected'}
  Testing: {', '.join(self.technology.testing_frameworks) or 'None detected'}

Architecture:
  Style: {self.architecture.architectural_style}
  Patterns: {', '.join(self.architecture.patterns) or 'None detected'}
  Layers: {len(self.architecture.layers)} layer(s)

Quality:
  Overall Score: {self.quality.overall_score}/100
  SOLID: {self.quality.solid_compliance}/100
  DRY: {self.quality.dry_compliance}/100
  YAGNI: {self.quality.yagni_compliance}/100

Confidence: {self.overall_confidence.level.value} ({self.overall_confidence.percentage}%)
Agent Used: {'Yes' if self.agent_used else f'No ({self.fallback_reason})'}
""".strip()


class AnalysisError(Exception):
    """Base exception for analysis errors."""
    pass


class AgentInvocationError(AnalysisError):
    """Error during agent invocation."""
    pass


class ParseError(AnalysisError):
    """Error parsing agent response."""
    pass
