"""
Data Models for Template Manifests

Provides structured data models for template manifests including metadata,
technology stack information, architecture patterns, and intelligent placeholders.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FrameworkInfo(BaseModel):
    """Framework information with version and purpose."""
    name: str = Field(description="Framework name (e.g., 'FastAPI', 'React')")
    version: Optional[str] = Field(None, description="Framework version if detected")
    purpose: str = Field(description="Framework purpose: 'testing', 'ui', 'data', 'core', etc.")


class PlaceholderInfo(BaseModel):
    """Intelligent placeholder information."""
    name: str = Field(description="Placeholder name in {{...}} format (e.g., '{{ProjectName}}')")
    description: str = Field(description="Human-readable description of this placeholder")
    default_value: Optional[str] = Field(None, description="Default value if not provided")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    required: bool = Field(default=True, description="Whether this placeholder must be provided")


class TemplateManifest(BaseModel):
    """
    Template manifest structure (manifest.json)

    This is the primary metadata file for templates, used by:
    - taskwright init command to discover and apply templates
    - Template browsers to display template information
    - Validation systems to ensure template compatibility
    """
    schema_version: str = Field(default="1.0.0", description="Manifest schema version")

    # Core identity
    name: str = Field(description="Template identifier (kebab-case)")
    display_name: str = Field(description="Human-friendly display name")
    description: str = Field(description="Template description and use case")
    version: str = Field(default="1.0.0", description="Template version (semver)")
    author: Optional[str] = Field(None, description="Template author")

    # Technology stack
    language: str = Field(description="Primary programming language")
    language_version: Optional[str] = Field(None, description="Language version requirement")
    frameworks: List[FrameworkInfo] = Field(default_factory=list, description="Frameworks used")
    architecture: str = Field(description="Architecture pattern (e.g., 'Clean Architecture', 'Layered')")

    # Template structure
    patterns: List[str] = Field(default_factory=list, description="Design patterns used")
    layers: List[str] = Field(default_factory=list, description="Architectural layers")
    placeholders: Dict[str, PlaceholderInfo] = Field(default_factory=dict, description="Template placeholders")

    # Usage information
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    category: str = Field(description="Template category: 'backend', 'frontend', 'mobile', 'fullstack', etc.")
    complexity: int = Field(ge=1, le=10, description="Complexity score (1-10)")

    # Compatibility
    compatible_with: List[str] = Field(default_factory=list, description="Compatible templates")
    requires: List[str] = Field(default_factory=list, description="Required agents/tools")

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp (ISO 8601)")
    source_project: Optional[str] = Field(None, description="Original project path")
    confidence_score: float = Field(ge=0.0, le=100.0, description="AI analysis confidence score")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=False, by_alias=True)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "schema_version": "1.0.0",
                "name": "python-clean-architecture",
                "display_name": "Python Clean Architecture",
                "description": "Python template using Clean Architecture with FastAPI",
                "version": "1.0.0",
                "author": "John Doe",
                "language": "python",
                "language_version": ">=3.9",
                "frameworks": [
                    {"name": "FastAPI", "version": "0.104.0", "purpose": "core"},
                    {"name": "pytest", "version": "7.4.0", "purpose": "testing"}
                ],
                "architecture": "Clean Architecture",
                "patterns": ["Repository", "Dependency Injection", "CQRS"],
                "layers": ["Domain", "Application", "Infrastructure", "Presentation"],
                "placeholders": {
                    "ProjectName": {
                        "name": "{{ProjectName}}",
                        "description": "Name of the project",
                        "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
                        "required": True
                    }
                },
                "tags": ["python", "fastapi", "clean-architecture", "domain"],
                "category": "backend",
                "complexity": 6,
                "compatible_with": [],
                "requires": ["agent:python-domain-specialist"],
                "created_at": "2025-01-06T00:00:00Z",
                "source_project": "/path/to/project",
                "confidence_score": 85.5
            }
        }


class ManifestValidationError(Exception):
    """Exception raised when manifest validation fails."""
    pass
