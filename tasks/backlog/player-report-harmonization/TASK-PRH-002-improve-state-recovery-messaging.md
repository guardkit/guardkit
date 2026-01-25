---
id: TASK-PRH-002
title: Improve state recovery error messaging
status: backlog
task_type: feature
implementation_mode: direct
priority: medium
complexity: 2
wave: 2
parallel_group: player-report-harmonization-wave2-1
created: 2026-01-25T14:45:00Z
parent_review: TASK-REV-DF4A
feature_id: FEAT-PRH
tags:
  - autobuild
  - error-messaging
  - user-experience
dependencies:
  - TASK-PRH-001
---

# TASK-PRH-002: Improve State Recovery Error Messaging

## Problem Statement

The current error message "Player failed - attempting state recovery" is misleading when the Player actually succeeded but the report file is missing. This creates confusion in the logs.

## Current Behavior

```
✗ Player failed - attempting state recovery
   Error: Player report not found: .../player_turn_1.json
```

## Expected Behavior

Distinguish between actual failures and missing reports:

```
⚠ Player report missing - using state recovery
   Note: Implementation may have succeeded; recovering state from git
```

## Implementation Approach

In `autobuild.py`, update the error handling in the adversarial loop:

```python
except PlayerReportNotFoundError as e:
    # Report missing but implementation may have succeeded
    console.print("  [yellow]⚠ Player report missing - using state recovery[/yellow]")
    console.print("   [dim]Note: Implementation may have succeeded; recovering state from git[/dim]")
    # Attempt state recovery...

except PlayerImplementationError as e:
    # Actual failure
    console.print(f"  [red]✗ Player failed: {e}[/red]")
    # Handle failure...
```

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Update error handling messages |
| `guardkit/orchestrator/progress.py` | Update status display for recovery mode |

## Acceptance Criteria

- [ ] "Player report missing" message shown for `PlayerReportNotFoundError`
- [ ] "Player failed" message shown only for actual implementation failures
- [ ] Log output clearly distinguishes between missing report and failure
- [ ] No changes to actual recovery behavior

## Test Plan

1. Trigger missing report scenario and verify new message
2. Trigger actual failure and verify failure message unchanged
3. Verify log clarity in both scenarios

## Related

- **Review Task**: TASK-REV-DF4A
- **Depends On**: TASK-PRH-001 (should be done after report harmonization)
