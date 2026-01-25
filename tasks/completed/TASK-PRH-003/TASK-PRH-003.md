---
id: TASK-PRH-003
title: Add state recovery metrics to execution summary
status: completed
task_type: feature
implementation_mode: direct
priority: low
complexity: 2
wave: 2
parallel_group: player-report-harmonization-wave2-2
created: 2026-01-25T14:45:00Z
completed: 2026-01-25T10:41:31Z
parent_review: TASK-REV-DF4A
feature_id: FEAT-PRH
tags:
  - autobuild
  - metrics
  - observability
dependencies:
  - TASK-PRH-001
completed_location: tasks/completed/TASK-PRH-003/
organized_files:
  - TASK-PRH-003.md
implementation_summary: |
  Successfully implemented state recovery metrics tracking throughout the AutoBuild system.
  Added recovery_count field to OrchestrationResult, tracked recovery attempts in
  AutoBuildOrchestrator, added Recovered column to wave summary table, and implemented
  execution quality metrics showing clean vs recovered execution ratios.
---

# TASK-PRH-003: Add State Recovery Metrics to Execution Summary

## Problem Statement

Currently the execution summary doesn't distinguish between clean executions and those that required state recovery. This makes it harder to understand execution quality.

## Current Behavior

```
Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┤
│   1    │    3     │   ✓ PASS   │    3     │    -     │    7     │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────╯
```

## Expected Behavior

```
Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬───────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │ Recovered │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼───────────┤
│   1    │    3     │   ✓ PASS   │    3     │    -     │    7     │     2     │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴───────────╯

Execution Quality:
  Clean executions: 4/6 (67%)
  State recoveries: 2/6 (33%)
```

## Implementation Approach

### Step 1: Track Recovery Events

In `autobuild.py`, track when state recovery is triggered:

```python
self.recovery_count = 0

# In state recovery block
self.recovery_count += 1
```

### Step 2: Include in Task Result

```python
return AutoBuildResult(
    task_id=task_id,
    decision=decision,
    turns=turn,
    recovery_count=self.recovery_count,  # New field
)
```

### Step 3: Display in Summary

Update `WaveProgressDisplay` to show recovery column and quality metrics.

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Added recovery_count tracking |
| `guardkit/cli/display.py` | Added Recovered column and quality metrics |
| `guardkit/orchestrator/feature_orchestrator.py` | Calculate and pass recovery counts |

## Acceptance Criteria

- [x] Recovery count tracked per task
- [x] Wave summary includes "Recovered" column
- [x] Execution quality summary shows clean vs recovered ratio
- [x] No impact on execution behavior

## Test Plan

1. Run feature with mix of clean and recovered tasks
2. Verify recovery counts are accurate
3. Verify summary display is correct

## Related

- **Review Task**: TASK-REV-DF4A
- **Depends On**: TASK-PRH-001 (recovery tracking more meaningful after fix)

## Implementation Details

**Commit**: 56bf0e63 - Add state recovery metrics to execution summary

**Changes Made**:
1. Added `recovery_count: int = 0` field to `OrchestrationResult` dataclass
2. Added `self.recovery_count: int = 0` tracking in `AutoBuildOrchestrator.__init__`
3. Incremented counter in `_attempt_state_recovery` method
4. Passed `recovery_count` in all `OrchestrationResult` instantiations
5. Added `recovered: int = 0` field to `WaveRecord` dataclass
6. Updated `complete_wave()` method to accept `recovered` parameter
7. Added "Recovered" column to wave summary table
8. Added execution quality metrics section with clean/recovered percentages
9. Updated feature orchestrator to calculate recovered counts from wave results

**New Output Format**:
- Wave summary table now includes "Recovered" column showing tasks that needed state recovery
- Execution quality section shows percentage breakdown of clean vs recovered executions
