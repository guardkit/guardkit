"""
Data Models for Template Generation

Provides Pydantic models for representing templates, template collections,
and validation results.
"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class CodeTemplate(BaseModel):
    """Represents a generated code template."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "name": "GetProducts.cs.template",
                "original_path": "src/Domain/Products/GetProducts.cs",
                "template_path": "templates/Domain/Products/GetProducts.template",
                "content": "namespace {{ProjectName}}.Domain.{{EntityNamePlural}};",
                "placeholders": ["ProjectName", "EntityNamePlural", "Verb", "EntityName"],
                "file_type": "domain_operation",
                "language": "C#",
                "purpose": "Domain operation for querying products",
                "quality_score": 9.0,
                "patterns": ["Repository pattern", "Result type pattern"]
            }
        }
    )

    schema_version: str = Field(default="1.0.0", description="Template schema version")
    name: str = Field(description="Template file name")
    original_path: str = Field(description="Path to original example file")
    template_path: str = Field(description="Relative path where template should be saved")
    content: str = Field(description="Templated content with placeholders")
    placeholders: List[str] = Field(default_factory=list, description="List of placeholder names")
    file_type: Optional[str] = Field(None, description="Type of file (e.g., 'domain_operation')")
    language: Optional[str] = Field(None, description="Programming language")
    purpose: Optional[str] = Field(None, description="Purpose of the template")
    quality_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Quality score from analysis")
    patterns: List[str] = Field(default_factory=list, description="Design patterns demonstrated")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of template creation")


class TemplateCollection(BaseModel):
    """Collection of generated templates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "templates": [],
                "total_count": 15,
                "by_type": {
                    "domain_operation": 8,
                    "repository": 4,
                    "entity": 3
                }
            }
        }
    )

    templates: List[CodeTemplate] = Field(default_factory=list, description="List of templates")
    total_count: int = Field(description="Total number of templates")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by file type")
    generated_at: datetime = Field(default_factory=datetime.now, description="Collection timestamp")


class ValidationResult(BaseModel):
    """Result of template validation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "errors": [],
                "warnings": ["No placeholders found in template"]
            }
        }
    )

    is_valid: bool = Field(description="Whether template passed validation")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class GenerationError(Exception):
    """Base exception for template generation errors."""
    pass


class ValidationError(GenerationError):
    """Error during template validation."""
    pass


class PlaceholderExtractionError(GenerationError):
    """Error during placeholder extraction."""
    pass


class TemplateClaude(BaseModel):
    """Generated CLAUDE.md structure"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "architecture_overview": "# Architecture Overview\n\nMVVM pattern...",
                "technology_stack": "# Technology Stack\n\n- C#...",
                "project_structure": "# Project Structure\n\n```\nsrc/\n```",
                "naming_conventions": "# Naming Conventions\n\n...",
                "patterns": "# Patterns\n\n...",
                "examples": "# Examples\n\n...",
                "quality_standards": "# Quality Standards\n\n...",
                "agent_usage": "# Agent Usage\n\n...",
                "generated_at": "2024-01-15T10:30:00Z",
                "confidence_score": 0.87
            }
        }
    )

    schema_version: str = Field(default="1.0.0", description="Template schema version")
    architecture_overview: str = Field(description="Markdown describing architecture")
    technology_stack: str = Field(description="Markdown describing tech stack")
    project_structure: str = Field(description="Markdown describing folder structure")
    naming_conventions: str = Field(description="Markdown describing naming rules")
    patterns: str = Field(description="Markdown describing patterns to follow")
    examples: str = Field(description="Markdown with code examples")
    quality_standards: str = Field(description="Markdown with quality guidelines")
    agent_usage: str = Field(description="Markdown describing which agents to use when")
    generated_at: str = Field(description="ISO 8601 timestamp")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")

    def to_markdown(self) -> str:
        """Convert to complete CLAUDE.md content"""
        sections = [
            self.architecture_overview,
            self.technology_stack,
            self.project_structure,
            self.naming_conventions,
            self.patterns,
            self.examples,
            self.quality_standards,
            self.agent_usage
        ]
        return "\n\n".join(sections)


class AgentMetadata(BaseModel):
    """Metadata extracted from an agent definition file"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "domain-operations-specialist",
                "purpose": "Create domain operations following verb-entity pattern",
                "capabilities": [
                    "Generate domain operation classes",
                    "Apply ErrorOr pattern",
                    "Follow SOLID principles"
                ],
                "when_to_use": "When creating or modifying domain operations",
                "category": "domain"
            }
        }
    )

    name: str = Field(description="Agent name (filename without .md)")
    purpose: str = Field(description="Primary purpose of the agent")
    capabilities: List[str] = Field(default_factory=list, description="What the agent can do")
    when_to_use: str = Field(description="Guidance on when to use this agent")
    category: str = Field(description="Category: domain, ui, testing, architecture, etc.")
