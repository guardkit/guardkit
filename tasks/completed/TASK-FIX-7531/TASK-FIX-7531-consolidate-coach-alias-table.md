---
id: TASK-FIX-7531
title: Consolidate coach_validator alias table with task_types.py (eliminate duplicate)
task_type: refactor
parent_review: TASK-REV-7530
feature_id: FEAT-CF57
wave: 1
implementation_mode: task-work
complexity: 2
priority: critical
dependencies: []
status: completed
tags: [autobuild, coach-validator, alias-table, bug-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-02
---

# Task: Consolidate Coach Validator Alias Table

## Context

`coach_validator.py` defines its own `TASK_TYPE_ALIASES` dict (line 69) that is a **subset** of the canonical table in `task_types.py` (line 253). TASK-ABFIX-001 added `enhancement` to `task_types.py` but missed the coach_validator's local copy, causing FEAT-CF57 TASK-INST-012 to fail with `Invalid task_type value: enhancement` during Coach validation — even though the Player phase (which uses `task_types.py`) succeeded.

## Root Cause

Dual alias tables — two independent copies of the same data that can drift out of sync.

## Implementation

### Change Required

In `guardkit/orchestrator/quality_gates/coach_validator.py`:

1. **Remove** the local `TASK_TYPE_ALIASES` definition (lines 67-75)
2. **Import** from `task_types.py` instead:

```python
from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
```

3. Verify no other code in the file depends on the local alias table having different contents

### Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — Remove local alias table, update import

### Expected Interface

The `_resolve_task_type()` method (line 512) already references the module-level `TASK_TYPE_ALIASES`. After consolidation, it will use the imported version from `task_types.py` which includes `enhancement`.

## Acceptance Criteria

- [x] `coach_validator.py` imports `TASK_TYPE_ALIASES` from `task_types.py`
- [x] Local `TASK_TYPE_ALIASES` definition removed from `coach_validator.py`
- [x] `enhancement` resolves to `TaskType.FEATURE` in Coach validation path
- [x] All existing coach_validator tests pass
- [x] No regression in alias resolution for other task types

## Completion Notes

- Removed local `TASK_TYPE_ALIASES` dict (5 entries) from coach_validator.py lines 67-75
- Updated import line to include `TASK_TYPE_ALIASES` from `guardkit.models.task_types`
- The canonical table in `task_types.py` has 6 entries (includes `enhancement`) vs the old local copy's 5
- `__all__` re-export at line 3874 still works since the name is in scope via import
- 643 tests pass, 9 pre-existing failures unrelated to this change
- Verified all 6 aliases resolve correctly through `_resolve_task_type()` method
