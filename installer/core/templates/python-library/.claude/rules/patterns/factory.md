# Factory

## Overview

Factory functions for creating test data and configurable objects.

## Implementation

```python
# conftest.py
from dataclasses import dataclass

@dataclass
class MockUser:
    name: str = "test_user"
    email: str = "test@example.com"
    active: bool = True

def make_user(**overrides) -> MockUser:
    defaults = {"name": "test_user", "email": "test@example.com", "active": True}
    defaults.update(overrides)
    return MockUser(**defaults)
```

## Best Practices

- Use factory functions in conftest.py, not fixtures with mutable state
- Provide sensible defaults for all fields
- Accept **overrides for flexibility
- Keep factory functions simple and composable
