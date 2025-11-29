# Agent Invocation Enforcement Tasks

This directory contains 5 implementation tasks for improving agent invocation enforcement in the `/task-work` command, identified during the TASK-8D3F architectural review.

## Background

During execution of TASK-ROE-007g in the MyDrive project, Claude bypassed the required agent invocations for Phase 3 (Implementation) and Phase 4 (Testing), instead performing the work directly. The final report incorrectly listed agents as "used" when they were never invoked via the Task tool.

**Root Cause**: The `/task-work` protocol contains clear instructions but lacks automated enforcement mechanisms to verify compliance.

**Review Report**: [TASK-8D3F Review Report](/.claude/reviews/TASK-8D3F-review-report.md)

## Tasks

### Critical Priority (Implement First)

1. **[TASK-ENF2](TASK-ENF2-add-agent-invocation-tracking.md)** - Add Agent Invocation Tracking & Logging
   - **Effort**: 8-12 hours
   - **Impact**: HIGH - Foundation for all enforcement
   - **Dependencies**: None
   - **Wave**: 1 (Parallel)

2. **[TASK-ENF1](TASK-ENF1-add-pre-report-validation-checkpoint.md)** - Add Pre-Report Validation Checkpoint
   - **Effort**: 4-6 hours
   - **Impact**: HIGH - Prevents false reporting
   - **Dependencies**: TASK-ENF2
   - **Wave**: 2 (Sequential)

### High Priority

3. **[TASK-ENF3](TASK-ENF3-add-prominent-invocation-messages.md)** - Add Prominent Invocation Messages
   - **Effort**: 2-4 hours
   - **Impact**: MEDIUM - Improves visibility
   - **Dependencies**: None
   - **Wave**: 1 (Parallel)

4. **[TASK-ENF4](TASK-ENF4-add-phase-gate-checkpoints.md)** - Add Phase Gate Checkpoints
   - **Effort**: 6-8 hours
   - **Impact**: HIGH - Prevents bypass during execution
   - **Dependencies**: TASK-ENF2
   - **Wave**: 2 (Sequential)

### Medium Priority

5. **[TASK-ENF5](TASK-ENF5-update-agent-selection-table.md)** - Update Agent Selection Table
   - **Effort**: 1-2 hours
   - **Impact**: MEDIUM - Reduces confusion
   - **Dependencies**: None
   - **Wave**: 1 (Parallel)

## Implementation Strategy

See **[IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)** for detailed:
- Wave-based deployment approach
- Parallel execution strategy using Conductor
- Testing and validation workflow
- Rollout plan with risk mitigation

### Quick Summary

**Wave 1** (Parallel - 3 tasks):
- TASK-ENF2 (Tracking)
- TASK-ENF3 (Messages)
- TASK-ENF5 (Table Update)
- **Duration**: 12 hours (parallel) vs 18 hours (sequential)
- **Savings**: 6 hours

**Wave 2** (Sequential - 2 tasks):
- TASK-ENF1 (Pre-Report Validation) → depends on ENF2
- TASK-ENF4 (Phase Gate Checkpoints) → depends on ENF2
- **Duration**: 10-14 hours

**Total**: 22-26 hours with parallel execution

## Execution Commands

### Using Conductor (Recommended for Parallel Execution)

**Wave 1**:
```bash
# Create 3 parallel worktrees
conductor create wave-1-tracking --task=TASK-ENF2
conductor create wave-1-messages --task=TASK-ENF3
conductor create wave-1-table --task=TASK-ENF5

# Execute in parallel (3 terminals)
cd wave-1-tracking && /task-work TASK-ENF2
cd wave-1-messages && /task-work TASK-ENF3
cd wave-1-table && /task-work TASK-ENF5 --micro
```

**Wave 2**:
```bash
# After Wave 1 merged
conductor create wave-2-validation --task=TASK-ENF1
cd wave-2-validation && /task-work TASK-ENF1

# After ENF1 merged
conductor create wave-2-phase-gates --task=TASK-ENF4
cd wave-2-phase-gates && /task-work TASK-ENF4
```

### Sequential Execution (Fallback)

```bash
/task-work TASK-ENF2  # 8-12 hours
/task-work TASK-ENF3  # 2-4 hours
/task-work TASK-ENF5 --micro  # 1-2 hours
/task-work TASK-ENF1  # 4-6 hours (after ENF2)
/task-work TASK-ENF4  # 6-8 hours (after ENF2)
```

## Expected Outcomes

### After Wave 1 (Foundation + Visibility)

✅ Running log displays agent invocations
✅ Prominent messages show which agents are invoked
✅ Agent table references correct agents
✅ No blocking behavior yet (safe deployment)

### After Wave 2 (Enforcement)

✅ Protocol violations caught immediately (phase gates)
✅ False reporting prevented (pre-report validation)
✅ Tasks BLOCKED if agents not invoked
✅ MyDrive TASK-ROE-007g scenario would be caught

## Success Metrics

- **100% agent usage** - All tasks use agents correctly
- **0% false reporting** - Agents used list matches actual invocations
- **0% false positives** - No tasks incorrectly BLOCKED
- **User confidence** - "I can see which agents are being used"

## Files in This Directory

- `README.md` - This file
- `IMPLEMENTATION-GUIDE.md` - Detailed implementation strategy
- `TASK-ENF1-add-pre-report-validation-checkpoint.md` - Pre-report validation task
- `TASK-ENF2-add-agent-invocation-tracking.md` - Tracking and logging task
- `TASK-ENF3-add-prominent-invocation-messages.md` - Invocation messages task
- `TASK-ENF4-add-phase-gate-checkpoints.md` - Phase gate checkpoints task
- `TASK-ENF5-update-agent-selection-table.md` - Agent table update task

## Related Documentation

- [TASK-8D3F Review Report](/.claude/reviews/TASK-8D3F-review-report.md) - Comprehensive review findings
- [task-work.md](/installer/global/commands/task-work.md) - Command being enhanced
- [Agent Discovery Guide](/docs/guides/agent-discovery-guide.md) - How agent selection works
- [Conductor Documentation](https://conductor.build) - Parallel worktree management

---

**Created**: 2025-11-27
**Review**: TASK-8D3F
**Total Effort**: 21-32 hours (22-26 hours with parallel execution)
**Estimated Savings**: 6-8 hours using Conductor parallel execution
