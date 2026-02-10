# Fix: Feature Plan file_path Generation

**Parent Review**: TASK-REV-1BE3
**Feature ID**: FEAT-FP-FIX

## Problem

`/feature-plan` generates YAML with `file_path: .` for all tasks when `--feature-slug` is omitted from the `generate-feature-yaml` invocation. This prevents `_copy_tasks_to_worktree()` from copying task files to the worktree, causing `UNRECOVERABLE_STALL` in autobuild.

## Solution

4 fixes at different layers to prevent recurrence:

| Task | Fix | Layer |
|------|-----|-------|
| TASK-FIX-FP01 | Add `--feature-slug` to spec examples | Spec (root cause) |
| TASK-FIX-FP02 | Reject directory paths in `validate_feature()` | Validation |
| TASK-FIX-FP03 | Raise on copy failure instead of warning | Fail-fast |
| TASK-FIX-FP04 | Require `--feature-slug` in generator | Input validation |

## Execution

All 4 tasks can execute in parallel (Wave 1) - no dependencies between them.

## Files Affected

- `installer/core/commands/feature-plan.md` (FP01)
- `guardkit/orchestrator/feature_loader.py` (FP02)
- `guardkit/orchestrator/feature_orchestrator.py` (FP03)
- `installer/core/commands/lib/generate_feature_yaml.py` (FP04)
