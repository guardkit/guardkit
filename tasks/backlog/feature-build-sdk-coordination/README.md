# Feature: Fix feature-build SDK Coordination Gaps

## Overview

Implementation tasks to fix the coordination gaps between AutoBuild orchestrator and Claude Agent SDK identified in TASK-REV-F6CB.

## Problem Statement

The `/feature-build` command has a 100% failure rate due to three distinct coordination gaps:
1. Task files not copied to worktree
2. `task_work_results.json` never written after SDK execution
3. CoachValidator and AgentInvoker use inconsistent artifact paths

## Subtasks

| Task ID | Title | Mode | Wave | Effort |
|---------|-------|------|------|--------|
| TASK-FBSDK-001 | Copy task files to worktree during setup | task-work | 1 | 1 day |
| TASK-FBSDK-002 | Write task_work_results.json after SDK parse | task-work | 1 | 2 days |
| TASK-FBSDK-003 | Centralize TaskArtifactPaths for SDK coordination | task-work | 2 | 1 day |
| TASK-FBSDK-004 | Add implementation plan stub for feature tasks | task-work | 2 | 0.5 days |
| TASK-FBSDK-005 | Adjust SDK timeout strategy for feature-build | direct | 3 | 0.5 days |

## Dependencies

- Wave 1: No dependencies (can run in parallel)
- Wave 2: Depends on Wave 1 completion
- Wave 3: Depends on Wave 2 completion

## Success Criteria

- [ ] Feature-build completes successfully for simple tasks
- [ ] `task_work_results.json` is created after SDK execution
- [ ] Coach can validate Player results without "not found" errors
- [ ] Task files are present in worktree for state transitions

## Parent Review

- **Review Task**: TASK-REV-F6CB
- **Report**: `.claude/reviews/TASK-REV-F6CB-review-report.md`

## Estimated Effort

**Total**: 6 days

- Wave 1: 3 days (P0 blocking fixes)
- Wave 2: 1.5 days (P1 coordination)
- Wave 3: 0.5 days (P2-P3 optimization)
