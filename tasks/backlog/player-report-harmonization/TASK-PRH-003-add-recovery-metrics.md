---
id: TASK-PRH-003
title: Add state recovery metrics to execution summary
status: backlog
task_type: feature
implementation_mode: direct
priority: low
complexity: 2
wave: 2
parallel_group: player-report-harmonization-wave2-2
created: 2026-01-25T14:45:00Z
parent_review: TASK-REV-DF4A
feature_id: FEAT-PRH
tags:
  - autobuild
  - metrics
  - observability
dependencies:
  - TASK-PRH-001
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

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Track recovery count |
| `guardkit/orchestrator/schemas.py` | Add recovery_count to AutoBuildResult |
| `guardkit/cli/display.py` | Add Recovered column to wave summary |

## Acceptance Criteria

- [ ] Recovery count tracked per task
- [ ] Wave summary includes "Recovered" column
- [ ] Execution quality summary shows clean vs recovered ratio
- [ ] No impact on execution behavior

## Test Plan

1. Run feature with mix of clean and recovered tasks
2. Verify recovery counts are accurate
3. Verify summary display is correct

## Related

- **Review Task**: TASK-REV-DF4A
- **Depends On**: TASK-PRH-001 (recovery tracking more meaningful after fix)
