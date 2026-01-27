---
id: TASK-TPL-003
title: Create complete pyproject.toml template with all dependencies
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T22:40:00Z
completed: 2026-01-27T22:40:00Z
previous_state: in_review
state_transition_reason: Task completed - all acceptance criteria verified
priority: high
tags: [template, fastapi-python, dependencies, pyproject, packaging]
complexity: 3
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 1
implementation_mode: task-work
dependencies: [TASK-TPL-001]
conductor_workspace: fastapi-fixes-wave1-3
completed_location: tasks/completed/fastapi-template-fixes/TASK-TPL-003/
files_created:
  - installer/core/templates/fastapi-python/templates/config/pyproject.toml.template
files_modified:
  - installer/core/templates/fastapi-python/manifest.json
  - installer/core/templates/fastapi-python/README.md
  - installer/core/templates/fastapi-python/settings.json
---

# Task: Create complete pyproject.toml template with all dependencies

## Description

Create a complete `pyproject.toml.template` file with all runtime and development dependencies. Currently, the template's manifest.json lists 7 frameworks but provides no pyproject.toml, causing ModuleNotFoundError at runtime.

## Problem

- manifest.json lists: FastAPI, SQLAlchemy, Pydantic, Alembic, pytest, pytest-asyncio, httpx
- Template provides no pyproject.toml
- README references `requirements/dev.txt` that doesn't exist
- New projects fail immediately with missing dependencies

## Solution

Create `templates/config/pyproject.toml.template`:

```toml
[project]
name = "{{ProjectName}}"
version = "0.1.0"
description = "{{ProjectDescription}}"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "{{AuthorName}}", email = "{{AuthorEmail}}"}
]

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.12.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "email-validator>=2.0.0",
    "structlog>=24.0.0",
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.0.0",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "pre-commit>=3.5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true
```

## Acceptance Criteria

- [x] Create `templates/config/pyproject.toml.template` with complete dependencies
- [x] Add placeholders: ProjectName, ProjectDescription, AuthorName, AuthorEmail
- [x] Include all runtime dependencies from manifest.json
- [x] Include dev dependencies for testing/linting
- [x] Add tool configurations (pytest, ruff, mypy)
- [x] Update manifest.json placeholders section
- [x] Update README Quick Start to use pyproject.toml

## Files to Create/Modify

1. `installer/core/templates/fastapi-python/templates/config/pyproject.toml.template` (new)
2. `installer/core/templates/fastapi-python/manifest.json` (update placeholders)
3. `installer/core/templates/fastapi-python/README.md` (update Quick Start)
4. `installer/core/templates/fastapi-python/settings.json` (add pyproject conventions)

## Notes

- Remove references to requirements/*.txt in favor of pyproject.toml
- Use modern Python packaging (hatchling build backend)
- Include tool configurations inline for single-file setup
