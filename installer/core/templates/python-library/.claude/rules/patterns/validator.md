# Validator

## Overview

Input validation using Pydantic validators and custom validation functions.

## Implementation

```python
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

class InputData(BaseModel):
    """Validated input data."""

    name: str = Field(min_length=1, max_length=100, description="Item name")
    value: float = Field(ge=0.0, description="Non-negative value")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "name must not be blank"
            raise ValueError(msg)
        return v.strip()
```

## Best Practices

- Use Pydantic Field constraints (min_length, max_length, ge, le) for simple validation
- Use @field_validator for complex validation logic
- Raise ValueError with descriptive messages
- Validate at system boundaries, trust internal data
