---
id: TASK-FIX-0C22
title: Fix docker_fixtures.py postgresql DATABASE_URL missing +asyncpg dialect suffix
status: completed
task_type: implementation
priority: high
complexity: 2
created: 2026-02-18T18:30:00Z
updated: 2026-02-18T20:05:00Z
completed: 2026-02-18T20:05:00Z
tags: [autobuild, coach-validator, docker-fixtures, postgresql, asyncpg, bug-fix]
parent_review: TASK-REV-0E07
feature_id: FEAT-REV7EB05-fixes
related_tasks:
  - TASK-REV-0E07
  - TASK-REV-7EB05
  - TASK-FIX-A7F1
  - TASK-FIX-AE7E
  - TASK-FIX-70F3
  - TASK-FIX-4415
requires_infrastructure: []
---

# Task: Fix docker_fixtures.py postgresql DATABASE_URL missing +asyncpg dialect suffix

## Problem

TASK-DB-003 reaches UNRECOVERABLE_STALL after 6 turns because the Coach's independent test verification consistently fails with:

```
ModuleNotFoundError: No module named 'psycopg2'
ERROR tests/users/test_users.py — 1 error in 0.32s
```

This is a **collection-time** failure (not a test execution failure). It occurs because:

1. The Coach starts a PostgreSQL Docker container and exports `DATABASE_URL=postgresql://postgres:test@localhost:5433/test` into `os.environ`
2. pytest collects `tests/users/test_users.py` and imports `src.main` → `src.db.session` (via `tests/conftest.py`)
3. `src/db/session.py` calls `create_async_engine(str(settings.DATABASE_URL))` at module level
4. `settings.DATABASE_URL` reads from `os.environ`, getting `postgresql://...` (no dialect suffix)
5. SQLAlchemy's default driver for plain `postgresql://` is `psycopg2` (synchronous)
6. `psycopg2` is not installed → `ModuleNotFoundError`

**Root cause**: `docker_fixtures.py` exports `postgresql://` instead of `postgresql+asyncpg://`. asyncpg IS correctly installed (bootstrap installs it before Wave 2). The URL scheme is wrong.

**Impact**: All async PostgreSQL AutoBuild tasks that use `create_async_engine()` will fail the same way.

## Fix

### 1. `guardkit/orchestrator/docker_fixtures.py` — line 30

```python
# Before:
"env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},

# After:
"env_export": {"DATABASE_URL": "postgresql+asyncpg://postgres:test@localhost:5433/test"},
```

### 2. `tests/unit/test_docker_fixtures.py` — update 2 assertions

```python
# test_get_env_exports_postgresql_contains_database_url
# Before:
assert exports["DATABASE_URL"].startswith("postgresql://")
# After:
assert exports["DATABASE_URL"].startswith("postgresql+asyncpg://")

# test_start_infrastructure_containers_sets_env_vars
# Before:
assert os.environ["DATABASE_URL"].startswith("postgresql://")
# After:
assert os.environ["DATABASE_URL"].startswith("postgresql+asyncpg://")
```

## Acceptance Criteria

- [x] `docker_fixtures.py` PostgreSQL `env_export` uses `postgresql+asyncpg://` scheme
- [x] `test_get_env_exports_postgresql_contains_database_url` asserts `postgresql+asyncpg://` prefix
- [x] `test_start_infrastructure_containers_sets_env_vars` asserts `postgresql+asyncpg://` prefix
- [x] All existing `test_docker_fixtures.py` tests pass (45/45)
- [x] `test_coach_validator.py` tests pass (216/216, no regression)
- [x] No other tests reference `postgresql://` for the PostgreSQL fixture URL (grep check)

## Implementation Notes

### Scope

This is a **3-line change** across 2 files:
- 1 line in `guardkit/orchestrator/docker_fixtures.py`
- 2 assertion lines in `tests/unit/test_docker_fixtures.py`

No schema changes, no YAML changes, no Player code changes, no environment changes.

### Risk

Low. The `+asyncpg` dialect suffix is required for `create_async_engine()` with PostgreSQL. All current GuardKit templates (fastapi-python, react-fastapi-monorepo) use async SQLAlchemy.

**Future consideration** (not in scope): if synchronous PostgreSQL tasks are added later, add a `postgresql-sync` fixture variant with `postgresql://`.

### Verification

After implementing, re-run `guardkit autobuild feature FEAT-BA28` to confirm TASK-DB-003 proceeds past turn 1 without the psycopg2 error. The Player's implementation code is correct — only the test environment URL was wrong.

### Do NOT

- Add `bootstrap_packages` to feature YAML (field doesn't exist in schema, asyncpg is already installed)
- Change `coach_validator.py` classification logic
- Change `_is_psycopg2_asyncpg_mismatch` (that logic is correct; fix the URL instead)
- Add `psycopg2-binary` to any requirements (wrong fix direction)
