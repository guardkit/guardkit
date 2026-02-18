---
id: TASK-FIX-A7F1
title: Fix psycopg2 misclassification as infrastructure failure
status: completed
task_type: implementation
created: 2026-02-18T16:00:00Z
updated: 2026-02-18T16:30:00Z
completed: 2026-02-18T16:45:00Z
completed_location: tasks/completed/TASK-FIX-A7F1/
priority: high
tags: [autobuild, coach-validator, failure-classification, psycopg2]
complexity: 4
parent_review: TASK-REV-7EB05
feature_id: FEAT-REV7EB05-fixes
wave: 1
implementation_mode: task-work
related_tasks:
  - TASK-REV-7EB05
  - TASK-FIX-AE7E
  - TASK-FIX-4415
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-18T16:45:00Z
  tests_passed: 205
  tests_failed: 0
organized_files:
  - TASK-FIX-A7F1.md
---

# Task: Fix psycopg2 misclassification as infrastructure failure

## Description

`_classify_test_failure` in `coach_validator.py` promotes `ModuleNotFoundError: No module named 'psycopg2'` to `("infrastructure", "high")` because `psycopg2` is in `_KNOWN_SERVICE_CLIENT_LIBS`. When the project uses `asyncpg` (not `psycopg2`), this is a **Player code choice error**, not an infrastructure failure.

The misclassification causes the Coach to give the Player feedback saying "infrastructure/environment issues (not code defects)", with hints about mock fixtures or SQLite — actively wrong advice that can misdirect the Player away from fixing the real problem (removing the `psycopg2` import).

**Source**: Finding F2 from TASK-REV-7EB05 review report.

## Acceptance Criteria

- [x] `psycopg2` removed from `_KNOWN_SERVICE_CLIENT_LIBS` (or made context-aware)
- [x] `ModuleNotFoundError: No module named 'psycopg2'` classifies as `("infrastructure", "ambiguous")` when no context is available, not `("infrastructure", "high")`
- [x] When bootstrap dependency list is available and `psycopg2` is NOT in it, classification returns `("code", "high")` with context
- [x] Existing tests for `_classify_test_failure` still pass
- [x] New tests cover: psycopg2 not in bootstrap → code error; asyncpg not in bootstrap → infrastructure error

## Implementation Notes

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`

**Option B (minimal, recommended first step)**: Remove `psycopg2` from `_KNOWN_SERVICE_CLIENT_LIBS`. It will then fall through to `_INFRA_AMBIGUOUS` (which matches `ModuleNotFoundError`) → returns `("infrastructure", "ambiguous")`. This is safer than `high` and won't trigger conditional approval path.

```python
# Before:
_KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
    "psycopg2",   # ← remove this
    "asyncpg",
    ...
]

# After:
_KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
    # psycopg2 removed — ambiguous: may be wrong lib choice in asyncpg projects
    "asyncpg",
    ...
]
```

**Option A (fuller fix)**: Cross-reference against bootstrap deps. If the `task` dict is accessible at classification time, check `task.get("requires_infrastructure", [])` — if `postgresql` is declared but `psycopg2` is not in bootstrap packages, classify as `("code", "high")`. This requires passing task context to `_classify_test_failure`.

Implement Option B now. Option A can follow in a separate task if needed.

**Tests to update**: `tests/orchestrator/quality_gates/test_coach_validator.py` — any tests asserting `psycopg2` → `("infrastructure", "high")` should be updated to `("infrastructure", "ambiguous")`.

## Completion Summary

### What Was Fixed

**Root cause discovered during implementation:** `psycopg2` appeared in *two* places that both caused false `("infrastructure", "high")` classification:
1. `_KNOWN_SERVICE_CLIENT_LIBS` — directly promoted `ModuleNotFoundError` for psycopg2 to high
2. `_INFRA_HIGH_CONFIDENCE` — substring "psycopg2" in `"No module named 'psycopg2'"` also matched, meaning the task notes' Option B (remove from `_KNOWN_SERVICE_CLIENT_LIBS` only) was insufficient

### Changes Made

**`guardkit/orchestrator/quality_gates/coach_validator.py`:**
1. Removed `psycopg2` from `_KNOWN_SERVICE_CLIENT_LIBS` with explanatory comment
2. Restructured `_classify_test_failure` to check `ModuleNotFoundError` **before** `_INFRA_HIGH_CONFIDENCE` — critical to prevent substring match on "psycopg2" in the high-confidence list
3. Added optional `requires_infrastructure` parameter for bootstrap context check (AC3)
4. Updated call site to pass `task.get("requires_infrastructure")` into `_classify_test_failure`

**`tests/unit/test_coach_validator.py`:**
5. Added `TestClassifyTestFailurePsycopg2` class (6 new tests, all passing)

### Test Results
- **205 passed, 0 failed** (full suite)
- 6 new tests added, all green
