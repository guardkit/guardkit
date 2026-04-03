# Model

## Overview

Pydantic BaseModel for data validation and serialization.

## Implementation

```python
from __future__ import annotations

from pydantic import BaseModel, Field

class Config(BaseModel):
    """Configuration for the service."""

    name: str = Field(description="Service name")
    timeout: float = Field(default=30.0, ge=0.0, description="Request timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10, description="Max retry attempts")
```

## Best Practices

- Use `Field(description=...)` on all fields
- Use `default_factory` for mutable defaults
- Subclass both `str` and `Enum` for string enums
- Apply `ge`/`le` constraints on numeric fields
- Keep models as pure data containers (no I/O)
