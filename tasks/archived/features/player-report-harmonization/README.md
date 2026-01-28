# Player Report Harmonization

**Feature ID**: FEAT-PRH
**Status**: In Progress (1/3 complete)
**Parent Review**: [TASK-REV-DF4A](../../in_review/TASK-REV-DF4A-review-feature-build-adversarial-loop-validation.md)

## Problem Statement

During the adversarial cooperation loop validation review (TASK-REV-DF4A), we discovered that direct mode Player invocations write `task_work_results.json` but NOT `player_turn_N.json`. This causes the AutoBuild orchestrator to trigger unnecessary state recovery because it looks for `player_turn_N.json`.

**Symptoms**:
- "Player failed - attempting state recovery" messages for successful implementations
- Unnecessary git state detection runs
- Confusing log output

**Root Cause**:
- Direct mode path in `agent_invoker.py` only writes one file type
- AutoBuild orchestrator expects a different file type

## Solution Approach

1. **Harmonize report writing** - Write both file types for direct mode
2. **Improve messaging** - Distinguish "report missing" from "actual failure"
3. **Add metrics** - Track recovery events for observability

## Subtasks

| Task | Title | Priority | Mode | Wave | Status |
|------|-------|----------|------|------|--------|
| [TASK-PRH-001](../../completed/TASK-PRH-001/TASK-PRH-001.md) | Harmonize Player report writing | High | task-work | 1 | ✅ COMPLETED |
| [TASK-PRH-002](TASK-PRH-002-improve-state-recovery-messaging.md) | Improve error messaging | Medium | direct | 2 | 📋 Backlog |
| [TASK-PRH-003](TASK-PRH-003-add-recovery-metrics.md) | Add recovery metrics | Low | direct | 2 | 📋 Backlog |

## Quick Start

```bash
# Essential fix only (recommended)
/task-work TASK-PRH-001

# Full implementation
/feature-build FEAT-PRH
```

## Expected Outcome

After implementation:
- Direct mode executions proceed without false "Player failed" messages
- Logs clearly distinguish between failures and missing reports
- Execution summaries show recovery statistics

## Related

- **Review**: [TASK-REV-DF4A Review Report](../../../.claude/reviews/TASK-REV-DF4A-review-report.md)
- **Architecture Score**: 78/100 (from review)
- **Implementation Guide**: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
