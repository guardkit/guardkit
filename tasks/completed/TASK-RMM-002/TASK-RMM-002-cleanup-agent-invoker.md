---
id: TASK-RMM-002
title: Clean up manual references in agent_invoker
status: completed
created: 2026-01-31T16:00:00Z
updated: 2026-01-31T16:40:00Z
completed: 2026-01-31T16:40:00Z
priority: high
tags: [implementation-mode, cleanup, autobuild]
parent_review: TASK-GR-REV-002
implementation_mode: task-work
wave: 1
complexity: 3
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-RMM-002/
---

# Task: Clean Up Manual References in Agent Invoker

## Description

Remove any references to `manual` implementation mode in `agent_invoker.py`. Ensure unknown modes default to `task-work` behavior.

## Files Modified

- `guardkit/orchestrator/agent_invoker.py`
- `tests/unit/test_agent_invoker.py`

## Acceptance Criteria

- [x] No `if impl_mode == "manual"` conditionals exist
- [x] `_get_implementation_mode()` only returns `"direct"` or `"task-work"`
- [x] Unknown/missing modes default to `task-work`
- [x] grep for "manual" returns no implementation-mode-related matches
- [x] All tests pass

## Implementation Summary

### Changes Made

1. **Updated `_get_implementation_mode()` (lines 1859-1905)**:
   - Changed from returning raw frontmatter value to explicitly normalizing unknown modes
   - Now only returns `"direct"` or `"task-work"` (never any other value)
   - Added logging for unknown mode normalization (helpful for debugging legacy tasks)
   - Updated docstring to clarify behavior with unknown modes

2. **Added test `test_get_implementation_mode_unknown_normalized_to_task_work`**:
   - Verifies that legacy `manual` mode (and any other unknown modes) are normalized to `task-work`
   - Located in `tests/unit/test_agent_invoker.py::TestDirectModeRouting`

### Before

```python
if impl_mode:
    logger.debug(f"[{task_id}] Detected implementation_mode: {impl_mode}")
    return impl_mode  # Could return 'manual' or any other value
```

### After

```python
if impl_mode == "direct":
    logger.debug(f"[{task_id}] Detected implementation_mode: direct")
    return "direct"

if impl_mode and impl_mode != "task-work":
    logger.debug(
        f"[{task_id}] Unknown implementation_mode '{impl_mode}', "
        "normalizing to task-work"
    )

logger.debug(f"[{task_id}] Using implementation_mode: task-work")
return "task-work"  # Always returns task-work for non-direct modes
```

## Test Results

- **Tests Run:** 18 (TestDirectModeRouting class)
- **Passed:** 18 ✅ (100%)
- **Failed:** 0
- **New Test Added:** `test_get_implementation_mode_unknown_normalized_to_task_work`

## Notes

This task had minimal changes because `manual` mode was never explicitly handled in agent_invoker. The main issue was that `manual` fell through to `task-work` path, which then failed on plan verification. With TASK-RMM-001 complete, `manual` won't be assigned anymore, and now even legacy tasks with `implementation_mode: manual` will be properly normalized.
