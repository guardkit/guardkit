# Python Library Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **python-library-specialist** agent.

**Core documentation**: See [python-library-specialist.md](./python-library-specialist.md)

---

## Related Templates

- `templates/src/__init__.py.template` — Package initialization with version string, docstring using `{{ProjectName}}` and `{{Description}}` placeholders, and `from __future__ import annotations`.

## Code Examples

### Example 1: Package Initialization

From `templates/src/__init__.py.template`:

```python
"""{{ProjectName}} — {{Description}}."""

from __future__ import annotations

__version__ = "0.1.0"
```

### Key Patterns

- Use `from __future__ import annotations` for forward compatibility
- Define `__version__` for programmatic version access
- Use docstring with project name and description
- Include `py.typed` marker file for PEP 561 compliance

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
