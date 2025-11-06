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
