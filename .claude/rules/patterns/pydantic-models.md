---
paths: "**/models.py", "**/schemas.py"
---

# Pydantic v2 Model Patterns

These patterns are extracted from GuardKit's actual codebase.

## Basic Model Structure

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FrameworkInfo(BaseModel):
    """Framework information with version and purpose."""
    name: str = Field(description="Framework name (e.g., 'FastAPI', 'React')")
    version: Optional[str] = Field(None, description="Framework version if detected")
    purpose: str = Field(description="Framework purpose: 'testing', 'ui', 'data', 'core'")
```

## Field Definitions

### Required Fields

```python
name: str = Field(description="Template identifier (kebab-case)")
```

### Optional Fields with Defaults

```python
version: str = Field(default="1.0.0", description="Template version (semver)")
author: Optional[str] = Field(None, description="Template author")
```

### Collection Fields

```python
frameworks: List[FrameworkInfo] = Field(default_factory=list, description="Frameworks used")
placeholders: Dict[str, PlaceholderInfo] = Field(default_factory=dict, description="Template placeholders")
tags: List[str] = Field(default_factory=list, description="Searchable tags")
```

### Constrained Fields

```python
complexity: int = Field(ge=1, le=10, description="Complexity score (1-10)")
confidence_score: float = Field(ge=0.0, le=100.0, description="AI analysis confidence score")
```

## Nested Models

```python
class PlaceholderInfo(BaseModel):
    """Intelligent placeholder information."""
    name: str = Field(description="Placeholder name in {{...}} format")
    description: str = Field(description="Human-readable description")
    default_value: Optional[str] = Field(None, description="Default value if not provided")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    required: bool = Field(default=True, description="Whether placeholder must be provided")


class TemplateManifest(BaseModel):
    """Template manifest with nested models."""
    schema_version: str = Field(default="1.0.0")
    frameworks: List[FrameworkInfo] = Field(default_factory=list)
    placeholders: Dict[str, PlaceholderInfo] = Field(default_factory=dict)
```

## Serialization

### Model Dump Method

```python
class TemplateManifest(BaseModel):
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=False, by_alias=True)
```

### Usage

```python
manifest = TemplateManifest(name="my-template", ...)
data = manifest.to_dict()
json_str = json.dumps(data, indent=2)
```

## JSON Schema Examples

Provide examples for documentation:

```python
class TemplateManifest(BaseModel):
    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0.0",
                "name": "python-clean-architecture",
                "display_name": "Python Clean Architecture",
                "language": "python",
                "frameworks": [
                    {"name": "FastAPI", "version": "0.104.0", "purpose": "core"},
                    {"name": "pytest", "version": "7.4.0", "purpose": "testing"}
                ],
                "complexity": 6,
                "confidence_score": 85.5
            }
        }
```

## Dynamic Default Values

Use lambdas for dynamic defaults:

```python
from datetime import datetime

created_at: str = Field(
    default_factory=lambda: datetime.now().isoformat(),
    description="Creation timestamp (ISO 8601)"
)
```

## Custom Exceptions

```python
class ManifestValidationError(Exception):
    """Exception raised when manifest validation fails."""
    pass
```

## When to Use Pydantic vs Dataclass

**Use Pydantic when:**
- Data comes from external sources (JSON, API)
- Need validation (constraints, patterns)
- Need serialization with configuration
- Need JSON schema generation

**Use dataclass when:**
- Simple internal state containers
- No validation needed
- Need asdict() for JSON
- Minimal overhead preferred
