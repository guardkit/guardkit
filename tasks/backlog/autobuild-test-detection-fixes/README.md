# AutoBuild Test Detection Fixes (FEAT-ABF)

**Parent Review**: TASK-REV-F3BE — Analyse PostgreSQL DB integration autobuild stall
**Status**: Ready for implementation
**Tasks**: 4 (2 waves)
**Estimated Effort**: Low-Medium (~60 lines total across 2 files)

## Problem

The autobuild Player-Coach workflow stalls indefinitely on `feature` task types when test files are domain-named (e.g., `test_users.py`) rather than task-ID-named (e.g., `test_task_db_003_users.py`). Checkpoint commits between turns make test files invisible to git-based detection, and the fallback glob pattern is too restrictive. The Coach blocks with a zero-test anomaly that provides no actionable guidance, causing identical rejection feedback across all subsequent turns until stall detection terminates the task.

## Solution

Four targeted fixes across two files that provide defense-in-depth:

1. **TASK-ABF-001**: Remove conditional gate on `tests_written` population
2. **TASK-ABF-002**: Merge SDK output with git-enriched file lists instead of replacing
3. **TASK-ABF-003**: Add glob pattern and naming guidance to zero-test anomaly feedback
4. **TASK-ABF-004**: Add cumulative git diff as tertiary fallback for test detection

## Subtasks

| Wave | Task | Title | Complexity | Mode |
|------|------|-------|------------|------|
| 1 | TASK-ABF-001 | Fix tests_written conditional gate | 3 | task-work |
| 1 | TASK-ABF-002 | Fix output override merge | 3 | task-work |
| 2 | TASK-ABF-003 | Actionable zero-test feedback | 2 | task-work |
| 2 | TASK-ABF-004 | Cumulative git diff fallback | 5 | task-work |

## Quick Start

```bash
# Wave 1 (parallel)
/task-work TASK-ABF-001
/task-work TASK-ABF-002

# Wave 2 (after Wave 1 merges)
/task-work TASK-ABF-003
/task-work TASK-ABF-004
```

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for detailed execution strategy.
