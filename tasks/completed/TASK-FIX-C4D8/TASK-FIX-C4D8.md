---
id: TASK-FIX-C4D8
title: "Fix: Apply TASK_WORK_SDK_MAX_TURNS to Direct Mode _invoke_with_role"
status: completed
created: 2026-01-25T19:35:00Z
updated: 2026-01-25T19:45:00Z
completed: 2026-01-25T19:45:00Z
completed_location: tasks/completed/TASK-FIX-C4D8/
priority: critical
task_type: implementation
implementation_mode: direct
tags: [feature-build, bugfix, direct-mode, sdk-max-turns, autobuild]
complexity: 2
parent_review: TASK-REV-C4D7
related_tasks:
  - TASK-REV-BB80
  - TASK-REV-C4D7
organized_files:
  - TASK-FIX-C4D8.md
  - completion-report.md
---

# Task: Fix Direct Mode SDK max_turns

## Overview

Apply the same `TASK_WORK_SDK_MAX_TURNS` constant to `_invoke_with_role` method that was already applied to `_invoke_task_work_implement` in TASK-REV-BB80.

This is a **single-line fix** with high confidence based on the TASK-REV-C4D7 review.

## Root Cause (from TASK-REV-C4D7)

Direct mode tasks fail because `_invoke_with_role` uses `self.max_turns_per_agent` (15) instead of the required 50 turns for implementation.

## Implementation

### Change Required

**File**: `guardkit/orchestrator/agent_invoker.py`
**Line**: 1221

```python
# Before (broken):
max_turns=self.max_turns_per_agent,

# After (fixed):
# TASK-REV-C4D7: Direct mode also needs ~50 internal turns
max_turns=TASK_WORK_SDK_MAX_TURNS,
```

### Full Context (lines 1217-1224)

```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=allowed_tools,
    permission_mode=permission_mode,
    # TASK-REV-C4D7: Direct mode also needs ~50 internal turns
    max_turns=TASK_WORK_SDK_MAX_TURNS,
    model=model,
    setting_sources=["project"],
)
```

## Acceptance Criteria

- [ ] Change `max_turns=self.max_turns_per_agent` to `max_turns=TASK_WORK_SDK_MAX_TURNS` at line 1221
- [ ] Add comment referencing TASK-REV-C4D7
- [ ] Verify FEAT-FHE (task-work delegation) still works (no regression)
- [ ] Verify unit tests pass

## Verification (Post-Implementation)

After merging, re-run:
```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-F392 --max-turns 15
```

Expected:
- All 6 tasks should complete (vs 0 currently)
- Wave 1 parallel tasks (TASK-DOC-001, 002, 005) should pass
- Duration should be ~30-60 minutes (vs 54 seconds)

## Risk Assessment

**Risk Level**: Low
- Single-line change
- Same fix already proven to work for task-work delegation
- No behavioral change for Coach (which legitimately needs fewer turns)

## Notes

This completes the TASK-REV-BB80 fix by applying it to all SDK invocation paths.
