---
id: TASK-FBSDK-013
title: Fix stub creation autobuild config check in state_bridge.py
status: completed
created: 2026-01-19T18:30:00Z
updated: 2026-01-19T20:15:00Z
completed: 2026-01-19T20:15:00Z
priority: critical
tags: [feature-build, state-bridge, stub-creation, root-cause-fix]
complexity: 2
parent_review: TASK-REV-FB17
wave: 1
implementation_mode: task-work
depends_on: []
completed_location: tasks/completed/TASK-FBSDK-013/
---

# TASK-FBSDK-013: Fix Stub Creation Autobuild Config Check (CRITICAL)

> **✅ COMPLETED**: This task fixed the **root cause** of feature-build failures.
> Debug trace analysis revealed the SDK was never invoked because stub creation was skipped.

## Problem Statement (ROOT CAUSE)

**This was the root cause of feature-build failures.** Debug trace analysis (`docs/reviews/feature-build/grep_error.md`) revealed:

```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-FHA-001
```

The error occurred BEFORE SDK invocation because stub creation was skipped at `state_bridge.py:380-384`:

```python
# OLD CODE (BROKEN)
if not isinstance(autobuild_config, dict) or not autobuild_config:
    self.logger.debug(f"Task {self.task_id} has no autobuild config, skipping stub creation")
    return None  # ← ALL feature tasks exited here!
```

**Why this happened**: Feature tasks from `/feature-plan` have:
- `autobuild_state:` (runtime state added by orchestrator) ← **NOT checked**
- `implementation_mode: direct` or `task-work` ← **NOT checked**
- **NO** `autobuild:` config in frontmatter ← **This is what the check required**

## Investigation Results

### Question 1: Do feature tasks include autobuild frontmatter?

**Finding**: NO. Feature tasks from `/feature-plan` only include:
- `implementation_mode: task-work` or `direct`
- `wave: N`
- Standard fields (id, title, status, etc.)

They do NOT include `autobuild:` configuration.

### Question 2: Is the check intentional?

**Finding**: The check was intended to prevent stub creation for manual tasks, but was too restrictive. It should allow stubs for:
1. Tasks with explicit `autobuild:` config
2. Tasks with runtime `autobuild_state:` (added during execution)
3. Tasks with `implementation_mode: task-work` (from /feature-plan)

### Question 3: What triggers stub creation?

The code path:
1. `verify_implementation_plan()` is called
2. Checks for existing plan
3. If no plan found, calls `_create_stub_implementation_plan()`
4. Stub creation checks `autobuild_config` - **THIS WAS THE BLOCKER**

## Solution Implemented: Option B (Extended)

Changed the check to create stubs for tasks with:
1. Explicit `autobuild:` config (original behavior)
2. Runtime `autobuild_state:` (from autobuild orchestrator)
3. `implementation_mode: task-work` (feature tasks from /feature-plan)

```python
# NEW CODE (FIXED)
# Get implementation mode and autobuild_state (runtime field)
implementation_mode = frontmatter_data.get("implementation_mode")
autobuild_state = frontmatter_data.get("autobuild_state", {})

# Create stub for tasks in autobuild context OR with task-work implementation mode
has_autobuild_config = isinstance(autobuild_config, dict) and autobuild_config
has_autobuild_state = isinstance(autobuild_state, dict) and autobuild_state
is_task_work_mode = implementation_mode == "task-work"

should_create_stub = has_autobuild_config or has_autobuild_state or is_task_work_mode

if not should_create_stub:
    self.logger.debug(
        f"Task {self.task_id} not configured for stub creation "
        f"(autobuild_config={bool(has_autobuild_config)}, "
        f"autobuild_state={bool(has_autobuild_state)}, "
        f"implementation_mode={implementation_mode})"
    )
    return None
```

## Acceptance Criteria

- [x] Investigate: Check sample feature task frontmatter
- [x] Decide: Chose Option B (extended with autobuild_state support)
- [x] Implement: Applied solution to `guardkit/tasks/state_bridge.py:378-403`
- [x] Test: Added 8 new tests in `tests/unit/test_state_bridge.py` (TestStubCreation class)

## Tests Added

New test class `TestStubCreation` with 8 tests:
1. `test_stub_created_for_task_with_autobuild_config` - Original behavior preserved
2. `test_stub_created_for_task_with_implementation_mode_task_work` - NEW: Feature tasks work
3. `test_stub_created_for_task_with_autobuild_state` - NEW: Runtime state works
4. `test_stub_not_created_for_manual_task` - Regression: Manual tasks don't get stubs
5. `test_stub_not_created_for_direct_mode_without_autobuild` - Regression: Direct mode without autobuild
6. `test_stub_not_created_for_task_without_any_config` - Regression: Plain tasks
7. `test_existing_valid_plan_not_overwritten` - Idempotency preserved
8. `test_stub_content_includes_task_title` - Content quality

All 28 tests pass.

## Files Modified

| File | Purpose |
|------|---------|
| `guardkit/tasks/state_bridge.py:378-403` | Fixed autobuild config check |
| `tests/unit/test_state_bridge.py` | Added TestStubCreation class (8 tests) |

## Impact

- **CRITICAL**: This fix unblocks SDK invocation for feature-build
- Feature tasks from `/feature-plan` will now get stub implementation plans created
- SDK invocation can now proceed past the "Implementation plan not found" error
- Existing behavior preserved for tasks with explicit `autobuild:` config
- Manual and direct tasks without autobuild config continue to skip stub creation

## Completion Summary

- **Duration**: ~45 minutes
- **Tests**: 28 passed (8 new)
- **Root Cause**: Fixed
- **Unblocks**: FBSDK-010, FBSDK-011, and all feature-build operations
