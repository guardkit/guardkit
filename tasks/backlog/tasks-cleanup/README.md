# Feature: Tasks Directory Cleanup

**Parent Review**: TASK-REV-BL01
**Feature ID**: FEAT-CLEANUP
**Created**: 2026-01-26

## Problem Statement

The `tasks/` directory has accumulated inconsistencies over time:
- 24 tasks with status/directory mismatches
- 17 empty feature directories with no remaining subtasks
- 23 duplicate/obsolete feature-build review tasks
- 2 permanently blocked tasks that should be in obsolete
- 2 duplicate task files

## Solution Approach

Execute cleanup operations in priority order to restore task directory consistency.

## Subtasks

| Task ID | Title | Mode | Wave |
|---------|-------|------|------|
| TASK-CL-001 | Fix status/directory mismatches | direct | 1 |
| TASK-CL-002 | Archive empty feature directories | direct | 1 |
| TASK-CL-003 | Consolidate feature-build review tasks | direct | 2 |
| TASK-CL-004 | Move blocked tasks to obsolete | direct | 2 |
| TASK-CL-005 | Remove duplicate task files | direct | 2 |

## Execution Strategy

- **Wave 1**: Independent file moves (can run in parallel)
- **Wave 2**: Cleanup and consolidation (depends on Wave 1)

## Success Criteria

- All tasks in correct directory matching their frontmatter status
- No empty feature directories in backlog
- Single consolidated archive for FB review tasks
- Zero duplicate task files
