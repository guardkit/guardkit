---
paths: **/*.py
---

# Code Style Guide

## Language: Python >=3.10

### Naming Conventions

- Functions/variables: snake_case
- Classes: PascalCase
- Constants: UPPER_CASE
- Modules: snake_case
- Private modules: prefixed with `_` (e.g., `_internal.py`)

### Formatting

- Use ruff for linting and formatting
- Max line length: 100 characters
- Indent: 4 spaces
- Rules: E, F, W, I, N, UP

### Type Hints

- Required on all public API functions and methods
- Use `from __future__ import annotations` in all modules
- Include `py.typed` marker (PEP 561) in package root

### Docstrings

- Google-style docstrings on all public API
- Module-level docstring for every module

### Best Practices

- Use `from __future__ import annotations` at top of every module
- Prefer pathlib over os.path
- Use logging to stderr, never print()
- Use factory functions in conftest.py, not fixtures with mutable state
