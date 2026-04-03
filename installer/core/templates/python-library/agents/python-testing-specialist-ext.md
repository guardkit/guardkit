# Python Testing Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **python-testing-specialist** agent.

**Core documentation**: See [python-testing-specialist.md](./python-testing-specialist.md)

---

## Related Templates

- `templates/src/__init__.py.template` — The library package being tested, with version and public API exports.

## Code Examples

### Example 1: Library Module Under Test

From `templates/src/__init__.py.template`:

```python
"""{{ProjectName}} — {{Description}}."""

from __future__ import annotations

__version__ = "0.1.0"
```

### Key Testing Patterns

```python
import pytest
from {{project_name}} import __version__

def test_version_is_semver():
    """Library version follows semantic versioning."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
