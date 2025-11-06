"""
Pydantic Data Models for Template Settings

Provides structured data models for template settings including naming
conventions, file organization, layer mappings, and code style preferences.

These models align with the template-contracts.md specification and follow
architectural best practices (SRP, clear type hints, validation).
"""

from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class CaseStyle(str, Enum):
    """Case style options for naming conventions."""
    PASCAL_CASE = "PascalCase"
    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"
    KEBAB_CASE = "kebab-case"
    SCREAMING_SNAKE_CASE = "SCREAMING_SNAKE_CASE"


class TestLocation(str, Enum):
    """Test file location strategies."""
    SEPARATE = "separate"  # Tests in separate directory (e.g., tests/)
    ADJACENT = "adjacent"  # Tests next to source files
    MIRROR = "mirror"      # Tests mirror source structure


class NamingConvention(BaseModel):
    """Naming convention for an element type.

    Example:
        NamingConvention(
            element_type="domain_operation",
            pattern="{{Verb}}{{Entity}}.cs",
            case_style=CaseStyle.PASCAL_CASE,
            suffix=".cs",
            examples=["GetProducts.cs", "CreateOrder.cs"]
        )
    """
    element_type: str = Field(description="Type of element (class, interface, file, method, etc.)")
    pattern: str = Field(description="Pattern with placeholders (e.g., '{{Verb}}{{Entity}}')")
    case_style: CaseStyle = Field(description="Case style to use")
    prefix: Optional[str] = Field(None, description="Prefix before placeholder")
    suffix: Optional[str] = Field(None, description="Suffix after placeholder (e.g., '.cs')")
    examples: List[str] = Field(default_factory=list, description="Example names following this convention")

    class Config:
        use_enum_values = True


class FileOrganization(BaseModel):
    """File organization preferences.

    Example:
        FileOrganization(
            by_layer=True,
            by_feature=False,
            test_location=TestLocation.SEPARATE,
            max_files_per_directory=50
        )
    """
    by_layer: bool = Field(True, description="Organize files by architectural layer")
    by_feature: bool = Field(False, description="Organize files by feature/domain")
    test_location: TestLocation = Field(TestLocation.SEPARATE, description="Where to place test files")
    max_files_per_directory: Optional[int] = Field(None, description="Maximum files per directory")

    class Config:
        use_enum_values = True


class LayerMapping(BaseModel):
    """Layer configuration mapping.

    Example:
        LayerMapping(
            name="Domain",
            directory="src/Domain",
            namespace_pattern="{{ProjectName}}.Domain.{{SubPath}}",
            file_patterns=["*.cs", "!*Test.cs"]
        )
    """
    name: str = Field(description="Layer name (e.g., 'Domain', 'Application')")
    directory: str = Field(description="Relative path to layer directory")
    namespace_pattern: Optional[str] = Field(None, description="Namespace pattern with placeholders")
    file_patterns: List[str] = Field(default_factory=list, description="File glob patterns for this layer")


class CodeStyle(BaseModel):
    """Code style preferences.

    Example:
        CodeStyle(
            indentation="spaces",
            indent_size=4,
            line_length=120,
            trailing_commas=False
        )
    """
    indentation: str = Field("spaces", description="Indentation type: 'spaces' or 'tabs'")
    indent_size: int = Field(4, ge=1, le=8, description="Number of spaces/tabs per indent")
    line_length: Optional[int] = Field(None, ge=40, le=200, description="Maximum line length")
    trailing_commas: bool = Field(False, description="Whether to use trailing commas")


class TemplateSettings(BaseModel):
    """Complete template settings structure.

    This is the root model that gets serialized to settings.json.

    Example:
        TemplateSettings(
            schema_version="1.0.0",
            naming_conventions={
                "domain_operation": NamingConvention(...)
            },
            file_organization=FileOrganization(...),
            layer_mappings={
                "Domain": LayerMapping(...)
            },
            code_style=CodeStyle(...)
        )
    """
    schema_version: str = Field("1.0.0", description="Schema version for compatibility")

    # Core settings
    naming_conventions: Dict[str, NamingConvention] = Field(
        description="Naming conventions by element type"
    )
    file_organization: FileOrganization = Field(
        description="File organization preferences"
    )
    layer_mappings: Dict[str, LayerMapping] = Field(
        description="Layer configuration mappings"
    )

    # Optional settings
    code_style: Optional[CodeStyle] = Field(None, description="Code style preferences")
    generation_options: Optional[Dict[str, Any]] = Field(None, description="Additional generation options")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode='json', exclude_none=False)

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateSettings":
        """Create from dictionary."""
        return cls.model_validate(data)


class TemplateSettingsError(Exception):
    """Base exception for template settings errors."""
    pass


class ValidationError(TemplateSettingsError):
    """Settings validation error."""
    pass


class GenerationError(TemplateSettingsError):
    """Settings generation error."""
    pass
