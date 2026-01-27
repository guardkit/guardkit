# Implementation Guide: FastAPI Template Fixes

## Overview

This feature addresses 6 integration issues discovered during real-world testing of the fastapi-python template. The issues range from critical (blocking authentication) to low (pattern guidance).

**Parent Review:** TASK-REV-A7F3
**Feature ID:** FEAT-TPL-FIX
**Total Tasks:** 6
**Estimated Time:** 8-12 hours

## Wave Breakdown

### Wave 1: Critical Fixes (Parallel)

These tasks can be executed in parallel using Conductor workspaces.

| Task | Title | Priority | Mode | Workspace |
|------|-------|----------|------|-----------|
| TASK-TPL-001 | Replace passlib with direct bcrypt | Critical | task-work | fastapi-fixes-wave1-1 |
| TASK-TPL-002 | Fix transaction handling architecture | Critical | task-work | fastapi-fixes-wave1-2 |
| TASK-TPL-003 | Create complete pyproject.toml template | High | task-work | fastapi-fixes-wave1-3 |

**Dependencies:**
- TASK-TPL-003 depends on TASK-TPL-001 (bcrypt in dependencies)

**Conductor Execution:**
```bash
# Start 3 parallel workspaces
conductor spawn fastapi-fixes-wave1-1 "Start TASK-TPL-001"
conductor spawn fastapi-fixes-wave1-2 "Start TASK-TPL-002"
conductor spawn fastapi-fixes-wave1-3 "Start TASK-TPL-003"

# Or sequential in main workspace
/task-work TASK-TPL-001
/task-work TASK-TPL-002
/task-work TASK-TPL-003
```

### Wave 2: Quality-of-Life Fixes (Parallel)

These tasks can be executed in parallel after Wave 1 completes.

| Task | Title | Priority | Mode | Workspace |
|------|-------|----------|------|-----------|
| TASK-TPL-004 | Add complete alembic.ini template | Medium | direct | fastapi-fixes-wave2-1 |
| TASK-TPL-005 | Enhance README with venv emphasis | Medium | direct | fastapi-fixes-wave2-2 |
| TASK-TPL-006 | Add pydantic-constraints.md guide | Low | direct | fastapi-fixes-wave2-3 |

**Dependencies:**
- TASK-TPL-005 depends on TASK-TPL-003 (uses pyproject.toml in examples)

**Conductor Execution:**
```bash
# After Wave 1 completes
conductor spawn fastapi-fixes-wave2-1 "Start TASK-TPL-004"
conductor spawn fastapi-fixes-wave2-2 "Start TASK-TPL-005"
conductor spawn fastapi-fixes-wave2-3 "Start TASK-TPL-006"
```

## Implementation Modes

| Mode | Tasks | Description |
|------|-------|-------------|
| **task-work** | 001, 002, 003 | Full quality gates (architectural review, testing) |
| **direct** | 004, 005, 006 | Direct implementation (documentation/config only) |

## Task Details

### TASK-TPL-001: Replace passlib with direct bcrypt

**Problem:** passlib unmaintained since 2020, incompatible with bcrypt 5.x
**Solution:** Direct bcrypt usage in security.py.template
**Files:**
- `templates/core/security.py.template` (new)
- `manifest.json` (update)
- `README.md` (migration note)

### TASK-TPL-002: Fix transaction handling architecture

**Problem:** get_db() doesn't commit, CRUDBase compensates, custom queries fail
**Solution:** Auto-commit in get_db(), flush() in CRUDBase
**Files:**
- `templates/db/session.py.template` (update)
- `templates/crud/crud_base.py.template` (update)
- `.claude/rules/database/crud.md` (update)

### TASK-TPL-003: Create complete pyproject.toml template

**Problem:** No pyproject.toml, manifest lists 7 frameworks
**Solution:** Complete pyproject.toml.template with all dependencies
**Files:**
- `templates/config/pyproject.toml.template` (new)
- `manifest.json` (update placeholders)
- `README.md` (update Quick Start)

### TASK-TPL-004: Add complete alembic.ini template

**Problem:** Incomplete alembic.ini example missing logger sections
**Solution:** Complete alembic.ini.template
**Files:**
- `templates/config/alembic.ini.template` (new)
- `.claude/rules/database/migrations.md` (update)

### TASK-TPL-005: Enhance README with venv emphasis

**Problem:** venv presented as optional, no explanation of why needed
**Solution:** Update Quick Start with emphasis and troubleshooting
**Files:**
- `README.md` (update)

### TASK-TPL-006: Add pydantic-constraints.md guide

**Problem:** Over-constraining schemas can fail with valid third-party data
**Solution:** Pattern guide for constraint decisions
**Files:**
- `.claude/rules/patterns/pydantic-constraints.md` (new)

## Verification

After all tasks complete:

```bash
# Validate template structure
/template-validate installer/core/templates/fastapi-python/

# Expected: No critical errors, quality scores updated
```

## Post-Implementation

1. Update manifest.json quality scores to reflect actual state
2. Update `production_ready` field based on test results
3. Test with fresh project initialization:
   ```bash
   guardkit init fastapi-python test-project
   cd test-project
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   python -m uvicorn src.main:app --reload
   ```

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| New project setup | 2-4 hours | 5-10 minutes |
| Runtime failures | 100% | <1% |
| Data integrity issues | 30-40% | <1% |
| Template matches claims | No | Yes |
