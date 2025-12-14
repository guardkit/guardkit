---
id: TASK-INFRA-001
title: "Project setup with dependencies"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, setup, dependencies]
complexity: 2
parent_feature: application-infrastructure
wave: 1
implementation_mode: direct
conductor_workspace: infra-wave1-setup
estimated_effort: 30min
---

# Task: Project setup with dependencies

## Description

Create the initial project structure and dependency files for the FastAPI backend application.

## Implementation Mode

**Direct** - This is a straightforward setup task that doesn't require the full `/task-work` workflow.

## Deliverables

### 1. pyproject.toml

Create project configuration with:
- Project metadata (name, version, description)
- Python version requirement (>=3.11)
- Build system configuration
- Tool configurations (ruff, mypy, pytest)

### 2. Requirements Files

Create `requirements/` directory with:

**base.txt** (Production):
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.12.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```

**dev.txt** (Development):
```
-r base.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0
ruff>=0.1.0
mypy>=1.7.0
```

### 3. Source Directory Structure

Create initial directory structure:
```
src/
├── __init__.py
├── core/
│   └── __init__.py
└── users/
    └── __init__.py
tests/
├── __init__.py
└── users/
    └── __init__.py
```

### 4. Git Configuration

Create/update `.gitignore` with Python patterns.

## Acceptance Criteria

- [ ] `pyproject.toml` created with all metadata
- [ ] `requirements/base.txt` created with production deps
- [ ] `requirements/dev.txt` created with dev deps
- [ ] `src/` directory structure created
- [ ] `tests/` directory structure created
- [ ] Dependencies can be installed: `pip install -r requirements/dev.txt`

## Notes

This task creates the foundation for all subsequent tasks. Complete this first before starting other Wave 1 tasks.
