---
id: TASK-RMM-003
title: Convert existing manual tasks to task-work
status: completed
created: 2026-01-31T16:00:00Z
updated: 2026-01-31T17:30:00Z
completed: 2026-01-31T17:35:00Z
priority: medium
tags: [implementation-mode, migration, cleanup]
parent_review: TASK-GR-REV-002
implementation_mode: direct
wave: 2
complexity: 2
depends_on:
  - TASK-RMM-001
completed_location: tasks/completed/TASK-RMM-003/
---

# Task: Convert Existing Manual Tasks to Task-Work

## Description

Find and convert all existing tasks with `implementation_mode: manual` to `implementation_mode: task-work`.

## Files to Update

Based on grep results from the review:

### 1. Feature YAML
- `.guardkit/features/FEAT-GR-MVP.yaml` (line 136) - **Already updated** (note shows it was changed per TASK-GR-REV-001)

### 2. Worktree Task Files
- `.guardkit/worktrees/FEAT-GR-MVP/tasks/design_approved/TASK-GR-PRE-003-A-research-upsert.md` - **Updated**

### 3. Test Fixtures (if still referencing manual)
- `tests/unit/test_state_bridge.py` (lines 486, 495) - **Updated** to use `unknown` mode for backward compatibility testing
- `.guardkit/worktrees/FEAT-GR-MVP/tests/unit/test_state_bridge.py` - **Updated** to use `unknown` mode
- `tests/unit/test_agent_invoker.py` (line 4977) - **Kept as-is** - tests backward compatibility normalization of `manual` → `task-work`

## Changes Required

### For each file:

Change:
```yaml
implementation_mode: manual
```

To:
```yaml
implementation_mode: task-work
```

### Verification

After changes, run:
```bash
grep -r "implementation_mode.*manual" tasks/ .guardkit/ tests/
```

Should return no matches (except documentation/examples and backward compatibility tests).

## Acceptance Criteria

- [x] No task files have `implementation_mode: manual` in frontmatter
- [x] No feature YAMLs have tasks with `manual` mode (already updated per TASK-GR-REV-001)
- [x] Test fixtures updated (or tests removed if testing manual mode specifically)
  - `test_state_bridge.py`: Renamed test to use `unknown` mode for backward compat
  - `test_agent_invoker.py`: Kept test for `manual` → `task-work` normalization (correct backward compat)
- [x] grep verification returns empty results for actual frontmatter

## Implementation Summary

### Changes Made

1. **`.guardkit/worktrees/FEAT-GR-MVP/tasks/design_approved/TASK-GR-PRE-003-A-research-upsert.md`**
   - Changed `implementation_mode: manual` → `implementation_mode: task-work`
   - This is a research/documentation task; the task_type field indicates its nature

2. **`tests/unit/test_state_bridge.py`**
   - Renamed `test_stub_not_created_for_manual_task` → `test_stub_not_created_for_unknown_mode`
   - Changed test fixture to use `implementation_mode: unknown` instead of `manual`
   - Added documentation explaining this tests backward compatibility

3. **`.guardkit/worktrees/FEAT-GR-MVP/tests/unit/test_state_bridge.py`**
   - Same changes as main repo test file

4. **`tests/unit/test_agent_invoker.py`**
   - **Kept as-is** - This test (`test_get_implementation_mode_unknown_normalized_to_task_work`)
     intentionally tests that `manual` mode is normalized to `task-work` at runtime
   - This is correct backward compatibility behavior per TASK-RMM-001

### Verification Results

```bash
# No task frontmatter with manual mode (only documentation examples remain)
grep -rn "^implementation_mode: manual$" tasks/ .guardkit/features/ .guardkit/worktrees/*/tasks/
# Result: Only found in TASK-RMM-003 example code block (this file)

# Tests pass
pytest tests/unit/test_state_bridge.py::TestStubCreation::test_stub_not_created_for_unknown_mode -v
# PASSED

pytest tests/unit/test_agent_invoker.py::TestDirectModeRouting::test_get_implementation_mode_unknown_normalized_to_task_work -v
# PASSED
```

## Notes

Some files may already have been updated per TASK-GR-REV-001 findings. Verify current state before making changes.
