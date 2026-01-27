---
id: TASK-TPL-005
title: Enhance README with virtual environment emphasis
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T14:30:00Z
completed: 2026-01-27T14:30:00Z
priority: medium
tags: [template, fastapi-python, documentation, venv, python]
complexity: 2
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 2
implementation_mode: direct
dependencies: [TASK-TPL-003]
conductor_workspace: fastapi-fixes-wave2-2
---

# Task: Enhance README with virtual environment emphasis

## Description

Update the README Quick Start section to emphasize virtual environment usage and explain why it's critical. Multiple Python installation conflicts are common, causing "packages installed but not found" issues.

## Problem

Current README Quick Start:

```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt
```

**Issues:**
- venv presented as optional step, not critical requirement
- No explanation of WHY venv is needed
- References non-existent requirements/dev.txt
- Doesn't mention `python -m` invocation pattern

## Solution

Update README Quick Start:

```markdown
## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (or use Docker)

### Setup

**CRITICAL: Always use a virtual environment to avoid package conflicts**

```bash
# Create and activate virtual environment (REQUIRED)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify you're in the venv (should show .venv/bin/python)
which python

# Install dependencies
python -m pip install -e ".[dev]"
```

> **Why virtual environments are required:**
> - Prevents conflicts between system Python and project Python
> - Ensures tools (pytest, alembic, uvicorn) find the right packages
> - Isolates project dependencies from global packages
> - Avoids "packages installed but not found" errors common with multiple Python installations

### Running the Application

```bash
# Always use python -m to ensure correct Python is used
python -m uvicorn src.main:app --reload

# Or use the venv path directly
.venv/bin/uvicorn src.main:app --reload
```

### Running Migrations

```bash
# Use python -m or venv path
python -m alembic upgrade head
# Or
.venv/bin/alembic upgrade head
```
```

## Acceptance Criteria

- [x] Update Quick Start section with venv emphasis
- [x] Add "Why virtual environments are required" explanation
- [x] Update commands to use pyproject.toml (`pip install -e ".[dev]"`)
- [x] Add `python -m` invocation pattern for all tools
- [x] Add troubleshooting section for common issues
- [x] Remove references to requirements/*.txt (already using pyproject.toml)

## Files to Modify

1. `installer/core/templates/fastapi-python/README.md`

## Troubleshooting Section to Add

```markdown
## Troubleshooting

### "ModuleNotFoundError" after pip install

This usually means you're not in the virtual environment:

```bash
# Check if venv is active
which python
# Should show: /path/to/project/.venv/bin/python

# If not, activate it
source .venv/bin/activate
```

### "Command not found" for uvicorn/pytest/alembic

Use `python -m` prefix or venv path:

```bash
python -m uvicorn src.main:app --reload
python -m pytest tests/
python -m alembic upgrade head
```
```

## Notes

- Documentation-only change
- High impact for developer experience
- Reduces support questions
