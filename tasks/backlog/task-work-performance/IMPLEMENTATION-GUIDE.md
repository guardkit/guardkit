# Implementation Guide: task-work Performance Optimization

## Overview

This guide outlines the execution strategy for optimizing `/task-work` performance based on TASK-REV-FB15 root cause analysis.

## Wave Breakdown

### Wave 1: Core Optimizations (Parallel Execution)

Both tasks can be worked on in parallel as they modify different parts of the system.

| Task | Focus Area | Conductor Workspace |
|------|------------|---------------------|
| TASK-TWP-a1b2 | Agent documentation constraints | task-work-perf-wave1-1 |
| TASK-TWP-c3d4 | Micro-mode threshold | task-work-perf-wave1-2 |

**Estimated Time**: 2-4 hours (parallel)
**Expected Impact**: 70-90% reduction in simple task duration

### Wave 2: Secondary Optimization

Depends on Wave 1 completion to verify overall improvement before adding MCP optimization.

| Task | Focus Area | Conductor Workspace |
|------|------------|---------------------|
| TASK-TWP-e5f6 | MCP conditional invocation | task-work-perf-wave2-1 |

**Estimated Time**: 1 hour
**Expected Impact**: Cleaner execution, no irrelevant results

## Execution Commands

### Wave 1 (Parallel)

```bash
# Terminal 1
cd .guardkit/worktrees/task-work-perf-wave1-1
/task-work TASK-TWP-a1b2

# Terminal 2
cd .guardkit/worktrees/task-work-perf-wave1-2
/task-work TASK-TWP-c3d4
```

Or with Conductor:
```bash
conductor workspace create task-work-perf-wave1-1
conductor workspace create task-work-perf-wave1-2
# Work in parallel in each workspace
```

### Wave 2 (After Wave 1 Complete)

```bash
/task-work TASK-TWP-e5f6 --micro  # Simple change, use micro mode
```

## Validation Strategy

### After Wave 1

Test that simple tasks complete faster:

```bash
# Create a complexity-3 test task
/task-create "Test performance: Add comment to README" complexity:3

# Should suggest --micro mode
/task-work TASK-XXX
# Expected: "Suggest using: /task-work TASK-XXX --micro"

# If not using micro, Phase 2 should complete in <15 minutes (was 58 min)
```

### After Wave 2

Verify MCP is skipped appropriately:

```bash
# Create task with known pattern
/task-create "Implement singleton for database connection" complexity:4

/task-work TASK-XXX
# Expected: "Skipping Pattern Suggestion: task references 'singleton' pattern"
```

## Success Metrics

| Metric | Baseline | Target | How to Measure |
|--------|----------|--------|----------------|
| Simple task duration | 65+ min | <10 min | Time full /task-work on complexity-3 task |
| Phase 2 tokens | 66k | <20k | Check SDK output logs |
| Micro-mode suggestion rate | Rare | Common | Count suggestions for simple tasks |
| MCP relevance | Irrelevant results | Skipped or relevant | Check Phase 2.5A output |

## Rollback Plan

If issues arise:
1. Revert to previous `task-work.md` version
2. Re-run installer to restore original agents
3. Document which specific change caused issues

All changes are additive (new validation, new skip logic) so rollback is straightforward.

## Dependencies

- No external dependencies
- All changes are to documentation and orchestration logic
- Tests can be run in isolation

## Related Documentation

- [TASK-REV-FB15 Review Report](/.claude/reviews/TASK-REV-FB15-review-report.md) - Root cause analysis
- [task-work.md](installer/core/commands/task-work.md) - Command specification
- [Micro-Task Mode Documentation](installer/core/commands/task-work.md#micro-task-mode) - Current micro-mode spec
