---
id: TASK-WC-013
title: Cleanup dead orchestrator code for clarification
status: backlog
task_type: implementation
created: 2025-12-13T23:00:00Z
updated: 2025-12-13T23:00:00Z
priority: low
tags: [clarification, cleanup, dead-code, wave-5]
complexity: 3
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 5
implementation_mode: direct
conductor_workspace: null
dependencies:
  - TASK-WC-012
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Cleanup Dead Orchestrator Code for Clarification

## Description

Remove the dead orchestrator code that was created for clarification but never invoked. With the unified subagent pattern, these orchestrators are no longer needed for clarification purposes.

## Background

The TASK-REV-CLQ2 review identified ~1,626 lines of dead orchestrator code:
- `feature_plan_orchestrator.py` (741 lines)
- `task_review_orchestrator.py` (885 lines) - **partial removal only**

These were created to handle clarification but the slash commands never invoked them.

## Files to Analyze

### Candidates for Removal

1. **`installer/core/commands/lib/feature_plan_orchestrator.py`** (741 lines)
   - Purpose: Orchestrate `/feature-plan` with clarification
   - Status: Never invoked, dead code
   - Action: **DELETE** (entire file)

2. **`installer/core/commands/lib/task_review_orchestrator.py`** (885 lines)
   - Purpose: Orchestrate `/task-review` with clarification
   - Status: May have non-clarification functionality
   - Action: **ANALYZE** - remove only clarification-related code

### Test Files to Remove

1. `tests/unit/commands/test_feature_plan_orchestrator.py`
2. `tests/unit/commands/test_task_review_orchestrator.py` (if orchestrator removed)
3. `tests/integration/lib/clarification/test_feature_plan_clarification.py`
4. `tests/integration/lib/clarification/test_task_review_clarification.py`

### Note: Keep template_create_orchestrator.py

`template_create_orchestrator.py` is NOT related to clarification and should be kept.

## Analysis Required

Before deleting, verify:

1. **Is task_review_orchestrator used for non-clarification purposes?**
   ```bash
   grep -n "execute_task_review\|task_review_orchestrator" installer/core/commands/*.md
   ```
   If used elsewhere, only remove clarification-specific code.

2. **Are there any symlinks pointing to these orchestrators?**
   ```bash
   ls -la ~/.agentecflow/bin/ | grep orchestrator
   ```
   If symlinks exist, they should also be removed.

3. **Do any other modules import these orchestrators?**
   Already checked - only test files import them.

## Changes Required

### Step 1: Remove feature_plan_orchestrator.py

```bash
rm installer/core/commands/lib/feature_plan_orchestrator.py
```

### Step 2: Analyze task_review_orchestrator.py

Check if it's used for anything other than clarification:
- If clarification-only: Delete entire file
- If mixed: Remove only clarification imports and functions

### Step 3: Remove Associated Tests

```bash
rm tests/unit/commands/test_feature_plan_orchestrator.py
rm tests/integration/lib/clarification/test_feature_plan_clarification.py
rm tests/integration/lib/clarification/test_task_review_clarification.py

# If task_review_orchestrator.py is fully removed:
rm tests/unit/commands/test_task_review_orchestrator.py
```

### Step 4: Update __init__.py Files

Remove any exports of deleted modules from `__init__.py` files.

### Step 5: Clean Up References in Documentation

Search for and remove references to orchestrators in:
- Documentation files
- Task files (mark as historical)

## Code to Remove (Summary)

| File | Lines | Action |
|------|-------|--------|
| `feature_plan_orchestrator.py` | 741 | DELETE |
| `task_review_orchestrator.py` | 885 | ANALYZE (may be partial) |
| `test_feature_plan_orchestrator.py` | ~200 | DELETE |
| `test_task_review_orchestrator.py` | ~200 | DELETE (if orchestrator removed) |
| `test_feature_plan_clarification.py` | ~150 | DELETE |
| `test_task_review_clarification.py` | ~150 | DELETE |
| **Total (estimated)** | **~2,300** | |

## Acceptance Criteria

- [ ] `feature_plan_orchestrator.py` deleted
- [ ] `task_review_orchestrator.py` analyzed and cleaned (or deleted)
- [ ] Associated test files deleted
- [ ] No broken imports in remaining code
- [ ] No symlinks pointing to deleted files
- [ ] `__init__.py` files updated
- [ ] Existing tests still pass (run full test suite)

## Testing

1. Run full test suite after deletions
2. Verify no import errors
3. Verify `/feature-plan` and `/task-review` still work (using subagent pattern)

## Notes

- This task should be done AFTER Wave 4 (smoke tests pass with subagent pattern)
- Priority is LOW because dead code doesn't break anything
- Consider keeping task files as historical reference (just mark completed)
- The clarification MODULE (`lib/clarification/*`) is NOT deleted - it's used by the subagent
