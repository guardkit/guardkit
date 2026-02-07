# Feature Specification: Task Lifecycle Cleanup

> **For**: `/feature-plan` command
> **Status**: Ready for Implementation
> **Created**: 2026-02-07
> **Architecture Score**: N/A (workflow improvement, not new architecture)

---

## Feature Overview

Improve task lifecycle management to reduce repository congestion caused by orphaned task files, stale feature directories, and incomplete cleanup after review terminal actions.

**Problem Solved**:
- Tasks directory contains 70+ individual backlog files and 30+ feature directories, many stale
- Completed directory has 400+ files and 200+ directories spanning months
- `task-review` terminal actions (Accept/Cancel/Implement) don't consistently complete tasks
- Feature directories persist after all tasks within them reach terminal state
- No mechanism to identify and clean up orphaned or stale task artifacts
- Repository clutter makes it harder to find active work and increases cognitive load

**Expected Outcomes**:
- 50-70% reduction in stale files in tasks/ directory
- Zero orphaned feature directories after terminal review actions
- Consistent task lifecycle: every task reaches a definitive terminal state
- Foundation for Dolt archival integration (separate feature spec)

---

## Scope

**Total Estimate**: 24-32 hours (~3-4 days)

### Wave 1: Task-Review Terminal Action Cleanup (8-10h)

Ensure that when `task-review` reaches a terminal action (Accept, Cancel, Implement), the underlying task is properly completed and moved to the appropriate terminal directory.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| TLC-001 | Audit current task-review terminal action handling - trace code paths for Accept/Cancel/Implement to identify gaps | task-review | 2h |
| TLC-002 | Implement auto-completion on Accept - when reviewer accepts, move task to `completed/` with completion metadata | task-work | 3h |
| TLC-003 | Implement auto-completion on Cancel - move task to `cancelled/` with cancellation reason | task-work | 2h |
| TLC-004 | Implement auto-completion on Implement - create implementation task in correct state, mark review as resolved | task-work | 2h |
| TLC-005 | Add tests for terminal action cleanup | task-work | 1h |

### Wave 2: Task-Complete Cleanup Mode (8-12h)

Extend `/task-complete` so that when invoked with no task ID argument, it enters a cleanup mode that identifies and processes stale tasks and directories.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| TLC-010 | Design cleanup mode interaction flow - what gets shown, how user confirms | task-review | 2h |
| TLC-011 | Implement stale task detection - find tasks in backlog/in_progress/in_review with no activity beyond configurable threshold (default: 14 days) | task-work | 3h |
| TLC-012 | Implement interactive cleanup prompt - list stale items, let user batch-select actions (complete, cancel, archive, skip) | task-work | 3h |
| TLC-013 | Implement feature directory sweep - detect feature dirs where all tasks are terminal, offer to clean up directory | task-work | 2h |
| TLC-014 | Add `--dry-run` flag to show what would be cleaned without acting | task-work | 1h |
| TLC-015 | Add `--auto` flag for non-interactive cleanup (use with caution, applies defaults) | task-work | 1h |

### Wave 3: Completed Directory Organisation (6-8h)

Improve the structure of the completed directory so historical tasks are easier to navigate and don't create a flat sprawl.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| TLC-020 | Implement date-based auto-organisation - completed tasks auto-filed into `YYYY-MM/` subdirectories (partially exists but inconsistent) | task-work | 2h |
| TLC-021 | Implement feature-grouped archival - when a feature's last task completes, bundle all its tasks into a single `completed/YYYY-MM/FEAT-slug/` directory | task-work | 3h |
| TLC-022 | Create one-time migration script to reorganise existing completed/ directory | task-work | 2h |
| TLC-023 | Update documentation for new lifecycle behaviour | direct | 1h |

---

## Acceptance Criteria

### Wave 1: Terminal Actions
- WHEN a task-review action is Accept THEN the task moves to completed/ with completion timestamp and review summary
- WHEN a task-review action is Cancel THEN the task moves to cancelled/ with cancellation reason
- WHEN a task-review action is Implement THEN the review task is resolved and implementation task is created/updated
- WHEN any terminal action occurs THEN no orphan files remain in the previous status directory

### Wave 2: Cleanup Mode
- WHEN `/task-complete` is run with no arguments THEN cleanup mode activates
- WHEN cleanup mode runs THEN it displays stale tasks grouped by status with last activity date
- WHEN user selects items THEN only selected items are processed (no silent bulk operations)
- WHEN `--dry-run` is used THEN output shows planned actions without executing
- WHEN feature directories contain only terminal tasks THEN they appear in cleanup suggestions

### Wave 3: Organisation
- WHEN a task completes THEN it is filed under `completed/YYYY-MM/` based on completion date
- WHEN the last task in a feature completes THEN all feature tasks are bundled together
- WHEN migration runs THEN existing completed/ files are reorganised without data loss

---

## Technical Notes

- This feature is a prerequisite for the Dolt archival integration (FEATURE-SPEC-dolt-task-archive)
- Cleanup mode should emit structured events that the Dolt archival pipeline can consume
- Stale detection should use file modification timestamps, not parse markdown content
- The `--auto` flag should be conservative: default to `skip` for anything ambiguous
- Feature directory detection needs to handle nested task structures (feature dirs containing subdirectories with their own tasks)

---

## Dependencies

- None (builds on existing task-complete and task-review infrastructure)

## Risks

- Aggressive cleanup could accidentally process tasks that are intentionally paused - mitigated by interactive confirmation and dry-run mode
- Date-based reorganisation changes paths that other tools might reference - mitigated by completing the migration before Dolt integration
