---
id: TASK-FIX-CKPT
title: Fix checkpoint test extraction JSON path and stall detection ordering
status: completed
completed: 2026-02-07
task_type: bugfix
parent_review: TASK-REV-AB01
complexity: 4
estimate_hours: 2
dependencies: []
---

# Fix checkpoint test extraction JSON path and stall detection ordering

## Description

Two bugs in the AutoBuild orchestrator cause false positive UNRECOVERABLE_STALL when Coach approves a task:

1. **Wrong JSON path in `_extract_tests_passed()`** (autobuild.py:2812-2826): Reads `validation_results.tests_passed` (top-level) but Coach stores the value at `validation_results.quality_gates.tests_passed` (nested). This causes every checkpoint to record `tests_passed=false` even when Coach reports tests as passing.

2. **Stall detection overrides Coach approval** (autobuild.py:1002-1065): The code flow is checkpoint creation -> stall detection -> approval check. If stall triggers at line 1042, it returns `unrecoverable_stall` BEFORE reaching the approval check at line 1063. A valid Coach approval is silently overridden.

These two bugs together caused the TASK-DM-002 false positive stall in the FEAT-D4CE autobuild run.

## Acceptance Criteria

- [x] `_extract_tests_passed()` reads `validation_results.quality_gates.tests_passed` as primary path
- [x] Falls back to `validation_results.tests_passed` for backward compatibility
- [x] Coach approval (`turn_record.decision == "approve"`) takes precedence over stall detection
- [x] Stall detection only applies when Coach gives "feedback" (not "approve")
- [x] Unit test: checkpoint records `tests_passed=true` when Coach report has `quality_gates.tests_passed=true`
- [x] Unit test: approval is returned even when stall conditions are met (2 consecutive failing checkpoints, no passing checkpoint, but Coach approves)
- [x] Existing stall detection tests continue to pass (legitimate stall cases still caught)

## Technical Details

### Bug 1: Fix `_extract_tests_passed()`

**File**: `guardkit/orchestrator/autobuild.py` (line ~2812)

**Current code**:
```python
validation = turn_record.coach_result.report.get("validation_results", {})
return validation.get("tests_passed", False)
```

**Coach report structure** (actual):
```json
{
  "validation_results": {
    "quality_gates": {
      "tests_passed": true
    }
  }
}
```

### Bug 2: Reorder approval check before stall detection

**File**: `guardkit/orchestrator/autobuild.py` (line ~1002-1065)

Either:
- Move the `if turn_record.decision == "approve"` check before the checkpoint/stall detection block
- Or add a guard: skip stall detection when `turn_record.decision == "approve"`

## Evidence

- Review report: `.claude/reviews/TASK-REV-AB01-review-report.md`
- Coach Turn 2 report showing approval overridden: `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/coach_turn_2.json`
- Checkpoint showing false `tests_passed=false`: `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/checkpoints.json`
