# Implementation Guide: Feature-Build Critical Fixes

## Overview

This guide provides the execution strategy for fixing feature-build critical bugs identified in TASK-REV-FB01.

## Wave Breakdown

### Wave 1: Critical Fixes (Parallel)

These tasks can run in parallel as they modify different files.

| Task | Files Modified | Conductor Workspace |
|------|----------------|---------------------|
| TASK-FB-RPT1 | `autobuild.py`, `agent_invoker.py`, tests | `feature-build-fixes-wave1-1` |
| TASK-FB-PATH1 | `coach_validator.py`, `coach_verification.py`, tests | `feature-build-fixes-wave1-2` |

**Execution**:
```bash
# Option 1: Sequential
/task-work TASK-FB-RPT1
/task-work TASK-FB-PATH1

# Option 2: Parallel with Conductor
conductor workspace create feature-build-fixes-wave1-1
conductor workspace create feature-build-fixes-wave1-2
# Run tasks in separate workspaces
```

**Estimated Duration**: 2-3 hours (parallel) or 3-4 hours (sequential)

### Wave 2: Configuration & Documentation (After Wave 1)

These are quick tasks that should only be done after Wave 1 fixes are verified.

| Task | Files Modified | Method |
|------|----------------|--------|
| TASK-FB-TIMEOUT1 | `agent_invoker.py:44`, `CLAUDE.md` | Direct edit |
| TASK-FB-DOC1 | `CLAUDE.md` | Direct edit |

**Execution**:
```bash
# These are simple enough to do directly
# No need for task-work overhead
```

**Estimated Duration**: 45 minutes

## Verification Steps

### After Wave 1

1. **Unit Tests**:
   ```bash
   pytest tests/unit/test_autobuild_orchestrator.py -v
   pytest tests/unit/test_coach_validator.py -v
   ```

2. **Integration Test**:
   ```bash
   # From terminal (not Claude Code)
   guardkit autobuild feature FEAT-TEST --sdk-timeout 900 --verbose
   ```

3. **Success Criteria**:
   - Player report found at correct path
   - Coach finds task_work_results.json
   - At least one turn completes without error

### After Wave 2

1. Verify default timeout is 600s:
   ```python
   from guardkit.orchestrator.agent_invoker import DEFAULT_SDK_TIMEOUT
   assert DEFAULT_SDK_TIMEOUT == 600
   ```

2. Review documentation changes in CLAUDE.md

## Total Effort

| Wave | Effort | Cumulative |
|------|--------|------------|
| Wave 1 | 2-3 hours | 2-3 hours |
| Wave 2 | 45 minutes | 3-4 hours |
| **Total** | | **3-4 hours** |

## Related Documentation

- Review Report: [TASK-REV-FB01-timeout-analysis-report.md](../../../.claude/reviews/TASK-REV-FB01-timeout-analysis-report.md)
- Evidence: [feature-build-output.md](../../../docs/reviews/feature-build/feature-build-output.md)
