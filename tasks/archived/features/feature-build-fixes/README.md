# Feature: Feature-Build Critical Fixes

## Problem Statement

The feature-build workflow fails despite the Player agent successfully implementing code. Root cause analysis (TASK-REV-FB01) identified two critical bugs in the reporting layer that cause every turn to be marked as "failed".

## Solution Approach

Fix the reporting layer bugs before increasing timeout, ensuring feature-build actually works end-to-end.

## Subtasks

| Task | Title | Priority | Mode | Wave |
|------|-------|----------|------|------|
| TASK-FB-RPT1 | Fix Player report writing | Critical | task-work | 1 |
| TASK-FB-PATH1 | Fix Coach validator path for feature mode | Critical | task-work | 1 |
| TASK-FB-TIMEOUT1 | Increase default SDK timeout to 600s | High | direct | 2 |
| TASK-FB-DOC1 | Document timeout recommendations | Low | direct | 2 |

## Execution Strategy

**Wave 1** (Critical - Parallel):
- TASK-FB-RPT1 and TASK-FB-PATH1 can run in parallel
- Both modify different files with no conflicts

**Wave 2** (After Wave 1):
- TASK-FB-TIMEOUT1 and TASK-FB-DOC1 are quick fixes
- Should only be done after Wave 1 confirms the fix

## Success Criteria

1. Player report found at correct path after turn completion
2. Coach finds task_work_results.json in feature worktree
3. At least one task completes with "approve" decision
4. Default timeout increased to 600s with documentation

## Related

- Review: [TASK-REV-FB01-timeout-analysis-report.md](../../../.claude/reviews/TASK-REV-FB01-timeout-analysis-report.md)
- Evidence: [feature-build-output.md](../../../docs/reviews/feature-build/feature-build-output.md)
- Existing task: TASK-SDK-e7f2 (superseded by TASK-FB-TIMEOUT1)
