# AutoBuild Stall Detection

**Parent Review**: TASK-REV-D4B1
**Feature**: FEAT-CR01 (Context Reduction via Graphiti Migration)

## Problem

TASK-CR-007 and TASK-CR-008 burned 55 turns (~50 minutes) in an unrecoverable loop because:
1. They were misclassified as `task_type: refactor` (requires tests) when they're documentation trimming tasks
2. The AutoBuild loop has no early exit when a stall is detected

## Tasks

| Task | Description | Priority | Wave | Mode |
|------|-------------|----------|------|------|
| TASK-FIX-D4B1 | Reclassify CR-007/CR-008 task types | Critical | 1 | direct |
| TASK-AB-SD01 | Add unrecoverable stall detection to AutoBuild | High | 1 | task-work |
| TASK-AB-SD02 | Add trim/reduce keywords to doc detector | Low | 2 | task-work |

## Execution

**Wave 1** (parallel):
- TASK-FIX-D4B1: Trivial YAML fix, do immediately
- TASK-AB-SD01: Stall detection implementation

**Wave 2** (after wave 1):
- TASK-AB-SD02: Keyword additions (depends on TASK-FIX-D4B1 for validation context)
