# Example RulesStructureGenerator Output

This document shows example output from RulesStructureGenerator.

## Generated Structure

```
.claude/
├── CLAUDE.md                          # Core (~5KB)
└── rules/
    ├── code-style.md                  # paths: **/*.py
    ├── testing.md                     # paths: **/*.test.*, **/tests/**
    ├── patterns/
    │   ├── repository-pattern.md
    │   └── service-layer.md
    └── agents/
        ├── repository-specialist.md   # paths: **/Repositories/**/*.cs, **/repositories/**/*.py
        ├── api-specialist.md          # paths: **/Controllers/**/*.cs, **/api/**/*.py
        └── testing-specialist.md      # paths: **/tests/**/*.*, **/*.test.*
```

## Example: CLAUDE.md

```markdown
# test/project

## Project Overview

This is a Python project using FastAPI, SQLAlchemy.
Architecture: Clean Architecture

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start development
uvicorn main:app --reload
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

**Language**: Python
**Frameworks**: FastAPI, SQLAlchemy
**Architecture**: Clean Architecture
```

## Example: rules/code-style.md

```markdown
---
paths: **/*.py, **/*.pyx
---

# Code Style Guide

## Language: Python

### Naming Conventions

- Functions/variables: snake_case
- Classes: PascalCase
- Constants: UPPER_CASE

### Formatting

- Use Black formatter
- Max line length: 88 characters
- Use type hints

### Best Practices

- Use list comprehensions
- Prefer f-strings
- Use context managers
```

## Example: rules/testing.md

```markdown
---
paths: **/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*
---

# Testing Guide

## Testing Frameworks

pytest

## Test Structure

- Unit tests: Test individual functions/methods
- Integration tests: Test component interactions
- E2E tests: Test full user workflows

## Coverage Requirements

- Minimum line coverage: 80%
- Minimum branch coverage: 75%
- All public APIs must have tests

## Test Naming

- test_<method_name>_<scenario>_<expected_result>
- Example: test_get_user_with_valid_id_returns_user
- Use descriptive names that explain the test

## Best Practices

- Keep tests focused and isolated
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
```

## Example: rules/guidance/repository-specialist.md

```markdown
---
paths: **/Repositories/**/*.cs, **/repositories/**/*.py
---

# repository-specialist

## Purpose

Agent for repository-specialist

## Capabilities

- repositories
- data-access

## Usage

This agent is automatically invoked when working on relevant files.

## Best Practices

- Follow agent guidance
- Review generated code
- Ask for clarification when needed
```

## Key Features

1. **Minimal Core**: CLAUDE.md is under 5KB, contains only essential info
2. **Path-Specific Loading**: Rules only load when relevant files are touched
3. **Frontmatter Filtering**: Uses YAML frontmatter with `paths:` for conditional loading
4. **Intelligent Path Inference**: Automatically maps agent names to relevant file patterns
5. **Modular Organization**: Separate files for code style, testing, patterns, and agents
