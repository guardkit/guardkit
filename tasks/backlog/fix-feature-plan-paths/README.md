# Fix Feature-Plan Path Generation

**Feature ID**: FEAT-FPP
**Parent Review**: TASK-REV-FP01
**Status**: Planned
**Tasks**: 5

## Problem

The `/feature-plan` command generates feature YAML files with invalid task file paths, causing `feature-build` to fail validation for all tasks. Two bugs:

1. **Duplicated directory segment**: `tasks/backlog/slug/slug/TASK-001.md` instead of `tasks/backlog/slug/TASK-001.md`
2. **Filename mismatch**: YAML records different slugified names than the files actually created on disk

## Solution

1. **Quick fix**: Correct FEAT-D4CE.yaml immediately (TASK-FPP-001)
2. **Unify slug generation**: Single shared function (TASK-FPP-002)
3. **Fix path doubling**: Guard in `build_task_file_path()` (TASK-FPP-003)
4. **Simplify spec**: Remove ambiguous 5-field format (TASK-FPP-004)
5. **Add validation**: Verify paths after YAML creation (TASK-FPP-005)

## Tasks

| ID | Title | Complexity | Mode | Wave |
|----|-------|-----------|------|------|
| TASK-FPP-001 | Fix FEAT-D4CE.yaml | 1 | direct | 1 |
| TASK-FPP-002 | Unify slug generation | 4 | task-work | 1 |
| TASK-FPP-003 | Fix path doubling | 3 | direct | 1 |
| TASK-FPP-004 | Simplify --task format | 2 | direct | 2 |
| TASK-FPP-005 | Add path validation | 4 | task-work | 2 |

## Execution Strategy

**Wave 1** (parallel - 3 tasks): TASK-FPP-001, TASK-FPP-002, TASK-FPP-003
**Wave 2** (parallel - 2 tasks): TASK-FPP-004, TASK-FPP-005 (depends on Wave 1)
