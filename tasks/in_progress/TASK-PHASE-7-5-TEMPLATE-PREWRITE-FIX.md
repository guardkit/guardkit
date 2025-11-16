---
status: in_progress
updated: 2025-11-16T09:50:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
priority: high
created: 2025-11-16
---

# TASK-PHASE-7-5-TEMPLATE-PREWRITE-FIX: Fix Phase 7.5 Template Pre-Write

**Priority**: High
**Created**: 2025-11-16
**Status**: In Progress

## Problem

Phase 7.5 (Agent Enhancement) finds 0 templates when it should find 15+ templates.

**Evidence from logs**:
```
INFO:installer.global.lib.template_creation.agent_enhancer:Found 10 agents and 0 templates
```

**Root Cause**: Templates are generated in Phase 4 (in memory) but not written to disk until Phase 9. Phase 7.5 runs between Phase 7 and Phase 8, but templates don't exist on disk yet, so `AgentEnhancer.enhance_all_agents()` finds 0 templates at line 120.

**Current fix location**: Lines 361-365 in `_complete_workflow()` - writes templates to disk before calling Phase 7.5.

**Why current fix doesn't work**: The fix is in the wrong code path. When executing from Claude Code CLI, the checkpoint-resume flow may not be triggering correctly, causing templates to never be written before Phase 7.5 scans for them.

## Acceptance Criteria

1. Phase 7.5 finds the correct number of templates (15 in test case)
2. Agent files are enhanced to 150-250 lines (vs current 30-40 lines)
3. Templates are written to disk BEFORE Phase 7.5 scans for them
4. Fix works in both normal execution and checkpoint-resume paths
5. No duplicate template writing (idempotent)

## Implementation Plan

### Step 1: Add Debug Logging
Add logging to trace execution flow:
- Log when `_run_all_phases()` is called
- Log when `_complete_workflow()` is called
- Log when templates are written to disk
- Log template count found by Phase 7.5

### Step 2: Verify Template Write Location
Ensure templates are written to disk in the correct location BEFORE Phase 7.5:
- After Phase 4 completes successfully
- Before Phase 7.5 calls `enhance_all_agents()`
- In BOTH code paths: `_run_all_phases()` and `_run_from_phase_5()`

### Step 3: Test the Fix
Run `/template-create --name test-fix --verbose` and verify:
- Logs show templates written to disk after Phase 4
- Phase 7.5 finds correct template count
- Agent files are 150-250 lines

### Step 4: Validate Idempotency
Ensure templates aren't written twice:
- Phase 4 completion writes templates
- Phase 9 checks if templates exist before writing

## Files to Modify

- `installer/global/commands/lib/template_create_orchestrator.py`
  - Add debug logging
  - Move/duplicate template pre-write to correct location
  - Ensure idempotent template writing

## Testing Strategy

1. Run `/template-create --name test-fix` on DeCUK.Mobile.MyDrive codebase
2. Check logs for template write before Phase 7.5
3. Verify Phase 7.5 finds 15 templates
4. Check agent file lengths (should be 150-250 lines)
5. Verify no duplicate template files written

## Success Metrics

- ✅ Phase 7.5 log shows "Found 10 agents and 15 templates" (not 0)
- ✅ Agent files are 150-250 lines (enhanced content)
- ✅ No errors or warnings about missing templates
- ✅ Templates exist in correct location before Phase 7.5 runs
