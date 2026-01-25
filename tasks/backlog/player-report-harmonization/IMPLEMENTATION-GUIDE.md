# Implementation Guide: Player Report Harmonization

## Feature Overview

**Feature ID**: FEAT-PRH
**Parent Review**: TASK-REV-DF4A
**Total Tasks**: 3
**Estimated Effort**: 2.5-4.5 hours

This feature addresses the Player report file inconsistency discovered during the adversarial cooperation loop validation review. The primary fix ensures direct mode Player invocations write `player_turn_N.json` alongside `task_work_results.json`, eliminating unnecessary state recovery triggers.

## Wave Breakdown

### Wave 1: Core Fix (1 task)

| Task | Title | Mode | Priority | Effort |
|------|-------|------|----------|--------|
| TASK-PRH-001 | Harmonize Player report writing | task-work | High | 1-2 hours |

**Dependencies**: None
**Parallel Execution**: Single task, execute directly

**What to do**:
```bash
/task-work TASK-PRH-001
```

**Verification**:
- Run a direct mode task
- Check both `task_work_results.json` AND `player_turn_N.json` exist
- Verify no "Player report not found" error

---

### Wave 2: UX Improvements (2 tasks)

| Task | Title | Mode | Priority | Effort |
|------|-------|------|----------|--------|
| TASK-PRH-002 | Improve state recovery messaging | direct | Medium | 0.5 hours |
| TASK-PRH-003 | Add recovery metrics to summary | direct | Low | 1 hour |

**Dependencies**: TASK-PRH-001 must be complete
**Parallel Execution**: These can run in parallel

**Conductor Workspaces**:
```bash
# Terminal 1
conductor new player-report-harmonization-wave2-1
/task-work TASK-PRH-002

# Terminal 2
conductor new player-report-harmonization-wave2-2
/task-work TASK-PRH-003
```

**Or Sequential**:
```bash
/task-work TASK-PRH-002
/task-work TASK-PRH-003
```

## Execution Strategy

### Recommended Approach

1. **Complete Wave 1 first** - This is the critical fix
2. **Verify the fix works** - Run a direct mode task end-to-end
3. **Wave 2 is optional** - These are UX improvements, not critical

### Quick Path (Essential Only)

If time is limited, just complete TASK-PRH-001. The other tasks are quality-of-life improvements.

## Files Affected

| File | Wave 1 | Wave 2 |
|------|--------|--------|
| `guardkit/orchestrator/agent_invoker.py` | ✅ | - |
| `guardkit/orchestrator/autobuild.py` | - | ✅ |
| `guardkit/orchestrator/progress.py` | - | ✅ |
| `guardkit/orchestrator/schemas.py` | - | ✅ |
| `guardkit/cli/display.py` | - | ✅ |

## Success Criteria

After completing this feature:

1. **No false "Player failed" messages** for successful direct mode executions
2. **Clearer distinction** between actual failures and missing reports
3. **Better observability** into execution quality (optional Wave 2)

## Related Documentation

- [Review Report](.claude/reviews/TASK-REV-DF4A-review-report.md)
- [Original Review](TASK-REV-2EDF)
- [Direct Mode Fix](TASK-FB-2D8B)
