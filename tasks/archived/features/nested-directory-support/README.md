# Feature: Nested Directory Support for AutoBuild CLI

## Problem Statement

The `/feature-plan` command creates tasks in nested feature subfolders:

```
tasks/backlog/application-infrastructure/
├── TASK-INFRA-001-project-structure-configuration.md
├── TASK-INFRA-002-database-infrastructure.md
└── ... (additional tasks)
```

However, the AutoBuild CLI (`guardkit autobuild task TASK-XXX`) only searches the top level of each state directory, causing it to fail to find these nested tasks.

## Solution

Update `TaskLoader._find_task_file()` to use `rglob` for recursive directory search, enabling discovery of tasks in feature subfolders.

## Origin

- **Review Task**: TASK-REV-C675
- **Review Report**: [.claude/reviews/TASK-REV-C675-review-report.md](../../../.claude/reviews/TASK-REV-C675-review-report.md)
- **Architecture Score**: 72/100

## Subtasks

| Task | Title | Priority | Mode | Status |
|------|-------|----------|------|--------|
| [TASK-NDS-001](TASK-NDS-001-update-taskloader-rglob.md) | Update TaskLoader to use rglob | High | task-work | Backlog |
| [TASK-NDS-002](TASK-NDS-002-add-nested-directory-tests.md) | Add nested directory tests | Medium | task-work | Backlog |
| [TASK-NDS-003](TASK-NDS-003-improve-error-messages.md) | Improve error messages | Low | direct | Backlog |

## Execution Strategy

**Wave 1** (Core):
- TASK-NDS-001: Update TaskLoader

**Wave 2** (Parallel):
- TASK-NDS-002: Add tests
- TASK-NDS-003: Improve errors

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for detailed execution instructions.

## Quick Start

```bash
# Start with Wave 1
/task-work TASK-NDS-001

# After Wave 1 completes, Wave 2 can run in parallel
/task-work TASK-NDS-002
# TASK-NDS-003 is direct implementation, no task-work needed
```

## Expected Outcome

After implementation:

1. `guardkit autobuild task TASK-XXX` finds tasks in nested directories
2. `/feature-build FEAT-XXX` works seamlessly with feature subfolders
3. Extended filenames (`TASK-XXX-name.md`) are properly matched
4. Error messages clearly indicate recursive search was performed

## Files Affected

- `guardkit/tasks/task_loader.py` (core change)
- `tests/unit/test_task_loader.py` (new tests)
