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


# ===== Phase 5.5 Completeness Validation Models (TASK-040) =====

class CompletenessIssue(BaseModel):
    """Represents a completeness validation issue"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "severity": "high",
                "type": "incomplete_crud",
                "message": "Product entity missing Update operation",
                "entity": "Product",
                "operation": "Update",
                "layer": "UseCases",
                "missing_files": ["UseCases/Products/UpdateProduct.cs"]
            }
        }
    )

    severity: str = Field(description="Issue severity: 'critical', 'high', 'medium', 'low'")
    type: str = Field(description="Issue type: 'incomplete_crud', 'layer_asymmetry', 'pattern_inconsistency'")
    message: str = Field(description="Human-readable issue description")
    entity: Optional[str] = Field(None, description="Entity name if applicable")
    operation: Optional[str] = Field(None, description="Operation name if applicable (Create, Read, Update, Delete, List)")
    layer: Optional[str] = Field(None, description="Layer name if applicable (Domain, UseCases, Web, Infrastructure)")
    missing_files: List[str] = Field(default_factory=list, description="List of missing file paths")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization"""
        return {
            'severity': self.severity,
            'type': self.type,
            'message': self.message,
            'entity': self.entity,
            'operation': self.operation,
            'layer': self.layer,
            'missing_files': self.missing_files
        }


class TemplateRecommendation(BaseModel):
    """Recommendation for missing template"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "UseCases/Products/UpdateProduct.cs",
                "reason": "Update operation missing for Product entity",
                "can_auto_generate": True,
                "reference_template": "UseCases/Products/CreateProduct.cs",
                "estimated_confidence": 0.85
            }
        }
    )

    file_path: str = Field(description="Recommended template file path")
    reason: str = Field(description="Why this template is recommended")
    can_auto_generate: bool = Field(description="Whether template can be auto-generated")
    reference_template: Optional[str] = Field(None, description="Reference template for auto-generation")
    estimated_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score 0-1")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization"""
        return {
            'file_path': self.file_path,
            'reason': self.reason,
            'can_auto_generate': self.can_auto_generate,
            'reference_template': self.reference_template,
            'estimated_confidence': self.estimated_confidence
        }


class ValidationReport(BaseModel):
    """Complete validation report with issues and recommendations"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_complete": False,
                "issues": [],
                "recommended_templates": [],
                "false_negative_score": 7.88,
                "templates_generated": 26,
                "templates_expected": 33,
                "validation_timestamp": "2025-01-07T10:30:00Z"
            }
        }
    )

    is_complete: bool = Field(description="Whether template collection is complete")
    issues: List[CompletenessIssue] = Field(default_factory=list, description="List of completeness issues")
    recommended_templates: List[TemplateRecommendation] = Field(default_factory=list, description="Recommended templates to add")
    false_negative_score: float = Field(ge=0.0, le=10.0, description="False negative score 0-10")
    templates_generated: int = Field(description="Number of templates generated")
    templates_expected: int = Field(description="Number of templates expected")
    validation_timestamp: str = Field(description="ISO 8601 timestamp of validation")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization"""
        return {
            'is_complete': self.is_complete,
            'issues': [issue.to_dict() for issue in self.issues],
            'recommended_templates': [rec.to_dict() for rec in self.recommended_templates],
            'false_negative_score': self.false_negative_score,
            'templates_generated': self.templates_generated,
            'templates_expected': self.templates_expected,
            'validation_timestamp': self.validation_timestamp
        }

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues"""
        return any(issue.severity == 'critical' for issue in self.issues)

    @property
    def has_high_severity_issues(self) -> bool:
        """Check if there are high severity issues"""
        return any(issue.severity in ['critical', 'high'] for issue in self.issues)


# ===== Phase 5.6 Split Output Models (TASK-PD-005) =====

class TemplateSplitMetadata(BaseModel):
    """Metadata for split template output validation and reporting (TASK-PD-007)

    This metadata provides structured metrics for validation reporting and
    orchestrator logging. It enables transparent visibility into split output
    quality and size reduction effectiveness.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "core_size_bytes": 8192,
                "patterns_size_bytes": 12288,
                "reference_size_bytes": 10240,
                "total_size_bytes": 30720,
                "reduction_percent": 73.33,
                "generated_at": "2025-12-05T10:30:00Z",
                "validation_passed": True,
                "validation_errors": []
            }
        }
    )

    core_size_bytes: int = Field(description="Size of core content in bytes")
    patterns_size_bytes: int = Field(description="Size of patterns content in bytes")
    reference_size_bytes: int = Field(description="Size of reference content in bytes")
    total_size_bytes: int = Field(description="Total size of all content in bytes")
    reduction_percent: float = Field(ge=0.0, le=100.0, description="Percentage reduction of core vs total")
    generated_at: str = Field(description="ISO 8601 timestamp of generation")
    validation_passed: bool = Field(description="Whether core content meets size constraints (≤10KB)")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages if any")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization"""
        return {
            'core_size_bytes': self.core_size_bytes,
            'patterns_size_bytes': self.patterns_size_bytes,
            'reference_size_bytes': self.reference_size_bytes,
            'total_size_bytes': self.total_size_bytes,
            'reduction_percent': self.reduction_percent,
            'generated_at': self.generated_at,
            'validation_passed': self.validation_passed,
            'validation_errors': self.validation_errors
        }


class TemplateSplitOutput(BaseModel):
    """Split CLAUDE.md output for progressive loading

    This model supports the transitional state where templates can generate
    both single-file (legacy) and split-file (new) CLAUDE.md outputs. Both
    formats remain fully supported to ensure backward compatibility.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "core_content": "# How to Load This Template\n...",
                "patterns_content": "# Patterns and Best Practices\n...",
                "reference_content": "# Code Examples\n...",
                "generated_at": "2025-12-05T10:30:00Z"
            }
        }
    )

    core_content: str = Field(description="Core CLAUDE.md content (≤10KB)")
    patterns_content: str = Field(description="Patterns and best practices section")
    reference_content: str = Field(description="Reference and examples section")
    generated_at: str = Field(description="ISO 8601 timestamp")
    metadata: Optional['TemplateSplitMetadata'] = Field(None, description="Optional metadata for validation and reporting (TASK-PD-007)")

    def get_core_size(self) -> int:
        """Calculate size of core content in bytes"""
        return len(self.core_content.encode('utf-8'))

    def get_patterns_size(self) -> int:
        """Calculate size of patterns content in bytes"""
        return len(self.patterns_content.encode('utf-8'))

    def get_reference_size(self) -> int:
        """Calculate size of reference content in bytes"""
        return len(self.reference_content.encode('utf-8'))

    def get_total_size(self) -> int:
        """Calculate total size of all content in bytes"""
        return self.get_core_size() + self.get_patterns_size() + self.get_reference_size()

    def get_reduction_percent(self) -> float:
        """Calculate percentage reduction of core vs total

        Returns:
            Percentage reduction (0-100)
        """
        total = self.get_total_size()
        if total == 0:
            return 0.0
        core = self.get_core_size()
        return ((total - core) / total) * 100.0

    def validate_size_constraints(self) -> tuple[bool, Optional[str]]:
        """Validate that core content meets size constraints with graceful degradation

        Returns:
            Tuple of (is_valid, error_message)
            error_message is None if valid
        """
        import logging

        core_size = self.get_core_size()
        max_core_size = 10 * 1024  # 10KB hard limit
        warning_size = 15 * 1024  # 15KB warning threshold

        if core_size > warning_size:
            # Exceeds warning threshold - fail with helpful message
            return False, f"Core content exceeds 15KB limit: {core_size / 1024:.2f}KB. Consider using --no-split for large codebases or further content optimization."
        elif core_size > max_core_size:
            # Between 10KB-15KB - log warning but allow (graceful degradation)
            logging.warning(f"Core content exceeds preferred 10KB limit but within acceptable range: {core_size / 1024:.2f}KB")
            return True, None

        return True, None

    def generate_metadata(self) -> 'TemplateSplitMetadata':
        """Generate metadata from current split output state (TASK-PD-007)

        Creates structured metadata including size metrics, validation status,
        and reduction percentage for validation reporting and orchestrator logging.

        Returns:
            TemplateSplitMetadata with current state metrics
        """
        is_valid, error = self.validate_size_constraints()
        errors = [] if is_valid else [error]

        return TemplateSplitMetadata(
            core_size_bytes=self.get_core_size(),
            patterns_size_bytes=self.get_patterns_size(),
            reference_size_bytes=self.get_reference_size(),
            total_size_bytes=self.get_total_size(),
            reduction_percent=self.get_reduction_percent(),
            generated_at=self.generated_at,
            validation_passed=is_valid,
            validation_errors=errors
        )
