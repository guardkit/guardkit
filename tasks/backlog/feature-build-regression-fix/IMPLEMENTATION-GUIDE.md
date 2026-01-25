# Implementation Guide: Feature-Build Regression Fix

**Feature ID**: FEAT-FBR
**Total Tasks**: 2
**Total Waves**: 1

## Wave Breakdown

### Wave 1: Parallel Fixes (2 tasks)

Both tasks can be executed in parallel as they modify different code paths.

| Task | Method | Workspace Name |
|------|--------|----------------|
| TASK-FBR-001 | task-work | feature-build-regression-fix-wave1-1 |
| TASK-FBR-002 | task-work | feature-build-regression-fix-wave1-2 |

## Execution Commands

### Option A: Sequential Execution

```bash
# Fix 1: Add recovery_count field (CRITICAL)
/task-work TASK-FBR-001

# Fix 2: Propagate max_turns parameter
/task-work TASK-FBR-002
```

### Option B: Parallel Execution (Conductor)

```bash
# Terminal 1
conductor worktree feature-build-regression-fix-wave1-1
/task-work TASK-FBR-001

# Terminal 2
conductor worktree feature-build-regression-fix-wave1-2
/task-work TASK-FBR-002
```

## Verification

After implementing both fixes:

1. Run the failing scenario:
   ```bash
   GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-FHE --max-turns 10
   ```

2. Verify:
   - No `AttributeError` on wave completion
   - Log shows `Max turns: 10` (not 50)

## Files Modified Summary

| Fix | Files |
|-----|-------|
| TASK-FBR-001 | `guardkit/orchestrator/feature_orchestrator.py` |
| TASK-FBR-002 | `guardkit/orchestrator/autobuild.py`, `guardkit/orchestrator/agent_invoker.py` |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Field addition breaks serialization | Default value (`recovery_count: int = 0`) ensures backward compatibility |
| Parameter propagation affects existing behavior | Value flows from CLI, so behavior only changes when CLI parameter is used |
