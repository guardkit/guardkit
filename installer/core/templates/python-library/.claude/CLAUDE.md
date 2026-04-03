# Python Library

## Project Overview

This is a Python library project using hatchling for build, pytest for testing, ruff for linting, and mypy for type checking.
Architecture: Src Layout Library

## Quick Start

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check .

# Run type checking
mypy src/

# Build package
python -m build
```

## Detailed Guidance

For detailed code style, testing patterns, architecture patterns, and agent-specific
guidance, see the `.claude/rules/` directory. Rules load automatically when you
work on relevant files.

- **Code Style**: `.claude/rules/code-style.md`
- **Testing**: `.claude/rules/testing.md`
- **Patterns**: `.claude/rules/patterns/`
- **Guidance**: `.claude/rules/guidance/`

## Technology Stack

**Language**: Python >=3.10
**Build**: hatchling (pyproject.toml)
**Testing**: pytest with asyncio_mode = "auto"
**Linting**: ruff (select = ["E", "F", "W", "I", "N", "UP"], line-length 100)
**Type Checking**: mypy (strict mode)
**Architecture**: Src Layout Library (`src/<package_name>/`)

## ALWAYS

- Add `from __future__ import annotations` to all modules
- Add `py.typed` (empty file) to the package directory — required for PEP 561
- Use type hints on all public API functions and methods
- Use Google-style docstrings on all public API functions
- Prefix private implementation modules with `_` (e.g., `_internal/`, `_utils.py`)
- Never import from `_internal/` in public-facing modules without explicit re-export
- Use stderr-only logging, never print()
- Use `conftest.py` factory function pattern (mock data classes + factory functions, not fixtures)
