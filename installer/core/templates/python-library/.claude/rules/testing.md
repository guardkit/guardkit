---
paths: **/*.test.*, **/tests/**, **/*_test.*, **/test_*.*,  **/conftest.py
---

# Testing Guide

## Testing Framework

pytest with asyncio_mode = "auto"

## Test Structure

- Unit tests: Test individual functions/methods in `tests/`
- Integration tests: Marked with `@pytest.mark.integration`
- Slow tests: Marked with `@pytest.mark.slow`
- Seam tests: Marked with `@pytest.mark.seam`

## Default Test Gate

```ini
# pyproject.toml
[tool.pytest.ini_options]
addopts = "-m 'not integration'"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests requiring external services",
    "seam: marks seam/boundary tests",
    "integration_contract: marks contract tests",
]
```

## Coverage Requirements

- Minimum line coverage: 80%
- Minimum branch coverage: 75%
- All public APIs must have tests

## Test Naming

- test_<function_name>_<scenario>_<expected_result>
- Example: test_parse_config_with_missing_key_raises_key_error

## conftest.py Pattern

Use factory functions, not fixtures with mutable state:

```python
# conftest.py
from dataclasses import dataclass

@dataclass
class MockConfig:
    name: str = "test"
    value: int = 42

def make_config(**overrides) -> MockConfig:
    defaults = {"name": "test", "value": 42}
    defaults.update(overrides)
    return MockConfig(**defaults)
```

## Best Practices

- Keep tests focused and isolated
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Zero network calls in unit tests
- Use factory functions over fixtures for test data
